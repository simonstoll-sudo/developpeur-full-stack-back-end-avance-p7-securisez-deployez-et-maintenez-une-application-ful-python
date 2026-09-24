from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

from django.test import TestCase

from .models import Destinataire, ReleveTemperature, Transport
from .services import enregistrer_releve, verifier_excursion


class ModelesTests(TestCase):
    def setUp(self):
        self.destinataire = Destinataire.objects.create(
            nom="Pharmacie des Tests",
            type_etablissement="PHARMACIE",
            adresse="1 rue du Test",
            code_postal="13000",
            ville="Marseille",
            email_contact="test@pharmacie.example",
            telephone_contact="04 00 00 00 00",
        )
        self.transport = Transport.objects.create(
            reference="TR-TEST-0001",
            type_produit="MEDICAMENT",
            destinataire=self.destinataire,
            temperature_min=Decimal("2.0"),
            temperature_max=Decimal("8.0"),
            date_depart=datetime(2024, 11, 4, 6, 30, tzinfo=dt_timezone.utc),
            date_arrivee_prevue=datetime(2024, 11, 4, 9, 0, tzinfo=dt_timezone.utc),
        )

    def test_str_transport(self):
        self.assertEqual(str(self.transport), "TR-TEST-0001")

    def test_str_destinataire(self):
        self.assertEqual(str(self.destinataire), "Pharmacie des Tests (Marseille)")

    def test_enregistrer_releve_dans_la_plage(self):
        releve = enregistrer_releve(self.transport.pk, "5.0")
        self.assertIsInstance(releve, ReleveTemperature)
        self.assertFalse(releve.hors_plage)
        self.assertEqual(releve.transport, self.transport)

    def test_verifier_excursion_au_dessus_du_max(self):
        self.assertTrue(verifier_excursion(self.transport, Decimal("9.5")))
