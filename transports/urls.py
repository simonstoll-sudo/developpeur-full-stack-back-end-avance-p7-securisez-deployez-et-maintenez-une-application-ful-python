from django.urls import path

from . import views

urlpatterns = [
    path("transports/", views.liste_transports, name="liste_transports"),
    path("transports/recherche/", views.recherche_transports, name="recherche_transports"),
    path("transports/<int:pk>/", views.detail_transport, name="detail_transport"),
    path("transports/<int:pk>/retard/", views.retard_transport, name="retard_transport"),
    path("transports/<int:pk>/releves/", views.releves_transport, name="releves_transport"),
    path("transports/<int:pk>/cloturer/", views.cloturer, name="cloturer_transport"),
    path("destinataires/", views.liste_destinataires, name="liste_destinataires"),
]
