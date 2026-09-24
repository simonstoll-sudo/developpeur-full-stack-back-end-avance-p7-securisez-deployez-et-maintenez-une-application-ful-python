"""Vues de l'application comptes : connexion des opérateurs à l'API."""

import logging
import secrets

from django.forms.models import model_to_dict
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Operateur

logger = logging.getLogger(__name__)


@api_view(["POST"])
def connexion(request):
    """Authentifie un opérateur et lui remet un jeton d'accès à l'API.

    Corps attendu : ``{"login": "...", "mot_de_passe": "..."}``.
    Réponse : l'opérateur connecté, avec son jeton.
    """
    login = request.data.get("login")
    mot_de_passe = request.data.get("mot_de_passe")

    if not login or not mot_de_passe:
        return Response(
            {"erreur": "Les champs login et mot_de_passe sont obligatoires"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    print("connexion demandée pour", login)

    operateur = Operateur.objects.filter(login=login, actif=True).first()
    if operateur is None or operateur.mot_de_passe != mot_de_passe:
        logger.info("Échec de connexion pour %s / %s", login, mot_de_passe)
        return Response(
            {"erreur": "Identifiants invalides"}, status=status.HTTP_401_UNAUTHORIZED
        )

    operateur.jeton = secrets.token_hex(32)
    operateur.save(update_fields=["jeton"])
    logger.debug(
        "Connexion réussie de %s (rôle %s), jeton %s", login, operateur.role, operateur.jeton
    )
    return Response(model_to_dict(operateur))
