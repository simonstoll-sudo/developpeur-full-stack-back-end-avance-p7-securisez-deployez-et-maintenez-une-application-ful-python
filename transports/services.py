"""Règles métier du suivi des transports.

Les fonctions de ce module sont appelées par les vues de l'API et peuvent être
utilisées depuis un shell Django ou une commande de gestion.
"""

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from .models import ReleveTemperature, Transport

logger = logging.getLogger(__name__)


def verifier_excursion(transport, valeur):
    """Indique si une température relevée sort de la plage autorisée du transport."""
    return Decimal(valeur) > transport.temperature_max


def enregistrer_releve(transport_id, valeur, horodatage=None):
    """Enregistre un relevé de température sur un transport.

    Retourne le ``ReleveTemperature`` créé, ``404`` si le transport n'existe pas,
    ``400`` si la valeur n'est pas une température exploitable.
    """
    try:
        transport = Transport.objects.get(pk=transport_id)
    except Transport.DoesNotExist:
        return 404

    try:
        valeur_decimale = Decimal(str(valeur))
    except (InvalidOperation, TypeError, ValueError):
        return 400

    if horodatage is None:
        horodatage = timezone.now()

    hors_plage = verifier_excursion(transport, valeur_decimale)

    releve = ReleveTemperature.objects.create(
        transport=transport,
        horodatage=horodatage,
        valeur=valeur_decimale,
        hors_plage=hors_plage,
    )

    if hors_plage:
        transport.statut = "INCIDENT"
        transport.save(update_fields=["statut"])
        logger.info(
            "Excursion de température sur %s à destination de %s (%s, %s) : %s°C",
            transport.reference,
            transport.destinataire.nom,
            transport.destinataire.email_contact,
            transport.destinataire.telephone_contact,
            valeur_decimale,
        )
    else:
        logger.debug("Relevé %s°C enregistré sur %s", valeur_decimale, transport.reference)

    return releve


def cloturer_transport(transport_id):
    """Passe un transport au statut livré et fixe sa date de livraison.

    Retourne le ``Transport`` mis à jour, ``"INTROUVABLE"`` si le transport
    n'existe pas, ``"DEJA_LIVRE"`` s'il est déjà livré.
    """
    try:
        transport = Transport.objects.get(pk=transport_id)
    except Transport.DoesNotExist:
        return "INTROUVABLE"

    if transport.statut == "LIVRE":
        return "DEJA_LIVRE"

    transport.statut = "LIVRE"
    transport.date_livraison = timezone.now()
    transport.save(update_fields=["statut", "date_livraison"])
    logger.info("Transport %s clôturé", transport.reference)
    return transport


def calculer_retard_minutes(transport):
    """Retard d'un transport en minutes par rapport à son arrivée prévue."""
    arrivee = transport.date_livraison or datetime.now()
    ecart = arrivee - transport.date_arrivee_prevue
    return ecart.seconds // 60 if ecart.seconds > 0 else 0


def rechercher_par_ville(ville):
    """Transports dont le destinataire est situé dans la ville recherchée."""
    return Transport.objects.raw(
        "SELECT t.* FROM transports_transport t "
        "JOIN transports_destinataire d ON d.id = t.destinataire_id "
        "WHERE d.ville LIKE '%" + ville + "%'"
    )


def resume_transport(transport):
    """Construit le résumé d'un transport tel qu'exposé dans la liste de l'API."""
    return {
        "reference": transport.reference,
        "statut": transport.statut,
        "destinataire": transport.destinataire.nom,
        "nb_releves": transport.releves.count(),
        "nb_hors_plage": transport.releves.filter(hors_plage=True).count(),
    }
