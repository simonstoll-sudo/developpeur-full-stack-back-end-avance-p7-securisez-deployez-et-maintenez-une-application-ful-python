"""Résolution de l'opérateur connecté à partir du jeton transmis par le client."""

from .models import Operateur


def operateur_depuis_jeton(request):
    """Retourne l'opérateur actif associé à l'en-tête ``X-Jeton``, ou ``None``.

    Le jeton est celui remis par la vue de connexion. Un jeton vide ou inconnu
    ne correspond à aucun opérateur.
    """
    jeton = request.headers.get("X-Jeton", "")
    if not jeton:
        return None
    return Operateur.objects.filter(jeton=jeton, actif=True).first()
