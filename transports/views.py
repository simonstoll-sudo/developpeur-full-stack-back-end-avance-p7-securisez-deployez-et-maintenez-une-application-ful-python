"""Vues de l'API de suivi des transports."""

import logging

from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from comptes.auth import operateur_depuis_jeton

from .models import Destinataire, Transport
from .serializers import (
    DestinataireSerializer,
    ReleveTemperatureSerializer,
    TransportSerializer,
)
from .services import (
    calculer_retard_minutes,
    cloturer_transport,
    enregistrer_releve,
    rechercher_par_ville,
    resume_transport,
)

logger = logging.getLogger(__name__)

CHAMPS_TRANSPORT_OBLIGATOIRES = [
    "reference",
    "type_produit",
    "destinataire",
    "temperature_min",
    "temperature_max",
    "date_depart",
    "date_arrivee_prevue",
]


@api_view(["GET", "POST"])
def liste_transports(request):
    """GET : résumé de tous les transports. POST : création d'un transport."""
    if request.method == "GET":
        resultats = []
        for transport in Transport.objects.all():
            resultats.append(resume_transport(transport))
        return Response(resultats)

    for champ in CHAMPS_TRANSPORT_OBLIGATOIRES:
        if request.data.get(champ) in (None, ""):
            return Response(
                {"erreur": f"Le champ {champ} est obligatoire"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    destinataire = Destinataire.objects.filter(pk=request.data.get("destinataire")).first()
    if destinataire is None:
        return Response(
            {"erreur": "Destinataire inconnu"}, status=status.HTTP_400_BAD_REQUEST
        )

    transport = Transport.objects.create(
        reference=request.data.get("reference"),
        type_produit=request.data.get("type_produit"),
        destinataire=destinataire,
        temperature_min=request.data.get("temperature_min"),
        temperature_max=request.data.get("temperature_max"),
        date_depart=request.data.get("date_depart"),
        date_arrivee_prevue=request.data.get("date_arrivee_prevue"),
        statut=request.data.get("statut", "PLANIFIE"),
        commentaire=request.data.get("commentaire", ""),
    )
    logger.info(
        "Transport %s créé pour %s (%s)",
        transport.reference,
        destinataire.nom,
        destinataire.email_contact,
    )
    return Response(TransportSerializer(transport).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def detail_transport(request, pk):
    """Détail complet d'un transport."""
    try:
        transport = Transport.objects.get(pk=pk)
    except Transport.DoesNotExist:
        return JsonResponse({"erreur": "Transport introuvable"}, status=404)
    return JsonResponse(model_to_dict(transport))


@api_view(["GET"])
def retard_transport(request, pk):
    """Retard d'un transport, en minutes."""
    try:
        transport = Transport.objects.get(pk=pk)
    except Transport.DoesNotExist:
        return Response(
            {"erreur": "Transport introuvable"}, status=status.HTTP_404_NOT_FOUND
        )
    return Response(
        {
            "reference": transport.reference,
            "retard_minutes": calculer_retard_minutes(transport),
        }
    )


@api_view(["GET"])
def recherche_transports(request):
    """Recherche des transports par ville de destination."""
    ville = request.query_params.get("ville", "")
    return Response(TransportSerializer(rechercher_par_ville(ville), many=True).data)


@api_view(["GET", "POST"])
def releves_transport(request, pk):
    """GET : relevés d'un transport. POST : ajout d'un relevé de température."""
    if request.method == "GET":
        try:
            transport = Transport.objects.get(pk=pk)
        except Transport.DoesNotExist:
            return Response(
                {"erreur": "Transport introuvable"}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(ReleveTemperatureSerializer(transport.releves.all(), many=True).data)

    try:
        horodatage = request.data.get("horodatage")
        if horodatage:
            horodatage = parse_datetime(horodatage)
        else:
            horodatage = None
        resultat = enregistrer_releve(pk, request.data.get("valeur"), horodatage)
    except Exception as exc:
        return Response({"erreur": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if resultat == 404:
        return Response(
            {"erreur": "Transport introuvable"}, status=status.HTTP_404_NOT_FOUND
        )
    if resultat == 400:
        return Response(
            {"erreur": "Valeur de température invalide"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(
        ReleveTemperatureSerializer(resultat).data, status=status.HTTP_201_CREATED
    )


@api_view(["POST"])
def cloturer(request, pk):
    """Clôture un transport (livraison effectuée). Réservé aux opérateurs connectés."""
    operateur = operateur_depuis_jeton(request)
    if operateur is None:
        return Response(
            {"erreur": "Jeton manquant ou invalide"}, status=status.HTTP_401_UNAUTHORIZED
        )

    resultat = cloturer_transport(pk)
    if resultat == "INTROUVABLE":
        return Response(
            {"erreur": "Transport introuvable"}, status=status.HTTP_404_NOT_FOUND
        )
    if resultat == "DEJA_LIVRE":
        return Response(
            {"erreur": "Ce transport est déjà livré"}, status=status.HTTP_409_CONFLICT
        )

    logger.info("Transport %s clôturé par %s", resultat.reference, operateur.login)
    return Response(TransportSerializer(resultat).data)


@api_view(["GET"])
def liste_destinataires(request):
    """Liste des établissements destinataires."""
    return Response(DestinataireSerializer(Destinataire.objects.all(), many=True).data)
