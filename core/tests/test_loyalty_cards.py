# core/tests/test_loyalty_cards.py

import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
from django.core.files.base import ContentFile
from core.models import LoyaltyCard
from core.utils.barcode_generator import BarcodeGenerator


class LoyaltyCardModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_loyalty_card_creation(self):
        card = LoyaltyCard.objects.create(
            user=self.user,
            store_name='Test Store',
            card_number='1234567890123',
            barcode_type='ean13',
            notes='Test notes'
        )
        self.assertEqual(card.store_name, 'Test Store')
        self.assertEqual(card.user, self.user)

    def test_loyalty_card_str(self):
        card = LoyaltyCard.objects.create(
            user=self.user,
            store_name='Conad',
            card_number='1234567890123',
            barcode_type='ean13'
        )
        self.assertEqual(str(card), 'Conad - 1234567890123')

    def test_loyalty_card_default_barcode_type(self):
        card = LoyaltyCard.objects.create(
            user=self.user,
            store_name='Test Store',
            card_number='ABC123'
        )
        self.assertEqual(card.barcode_type, 'code128')

    def test_loyalty_card_deleted_with_user(self):
        LoyaltyCard.objects.create(
            user=self.user,
            store_name='Test Store',
            card_number='123'
        )
        self.assertEqual(LoyaltyCard.objects.count(), 1)
        self.user.delete()
        self.assertEqual(LoyaltyCard.objects.count(), 0)


class BarcodeGeneratorTest(TestCase):
    def test_detect_ean13(self):
        result = BarcodeGenerator.detect_barcode_type('1234567890123')
        self.assertEqual(result, 'ean13')

    def test_detect_ean8(self):
        result = BarcodeGenerator.detect_barcode_type('12345678')
        self.assertEqual(result, 'ean8')

    def test_detect_upca(self):
        result = BarcodeGenerator.detect_barcode_type('123456789012')
        self.assertEqual(result, 'upca')

    def test_detect_code128_fallback(self):
        result = BarcodeGenerator.detect_barcode_type('ABC123')
        self.assertEqual(result, 'code128')

    def test_validate_ean13_valid(self):
        result = BarcodeGenerator.validate_code('1234567890123', 'ean13')
        self.assertTrue(result)

    def test_validate_ean13_invalid(self):
        result = BarcodeGenerator.validate_code('12345', 'ean13')
        self.assertFalse(result)

    def test_validate_code128_nonempty(self):
        result = BarcodeGenerator.validate_code('ABC123', 'code128')
        self.assertTrue(result)

    def test_validate_code128_empty(self):
        result = BarcodeGenerator.validate_code('', 'code128')
        self.assertFalse(result)

    def test_generate_barcode_returns_tuple(self):
        result = BarcodeGenerator.generate_barcode('ABC123', 'code128')
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_generate_barcode_autodetect(self):
        _, barcode_type = BarcodeGenerator.generate_barcode('1234567890123')
        self.assertEqual(barcode_type, 'ean13')


class LoyaltyCardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_list_view_requires_login(self):
        self.client.logout()
        response = self.client.get('/loyalty-cards/')
        self.assertIn(response.status_code, [301, 302])

    def test_list_view_returns_200(self):
        response = self.client.get('/loyalty-cards/', follow=True)
        self.assertEqual(response.status_code, 200)

    def test_list_view_shows_only_user_cards(self):
        other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        LoyaltyCard.objects.create(
            user=self.user,
            store_name='My Store',
            card_number='111'
        )
        LoyaltyCard.objects.create(
            user=other_user,
            store_name='Other Store',
            card_number='222'
        )
        response = self.client.get('/loyalty-cards/', follow=True)
        cards = response.context['cards']
        self.assertEqual(cards.count(), 1)
        self.assertEqual(cards.first().store_name, 'My Store')

    def test_detail_view_returns_200(self):
        card = LoyaltyCard.objects.create(
            user=self.user,
            store_name='Test Store',
            card_number='123'
        )
        response = self.client.get(f'/loyalty-cards/{card.id}/', follow=True)
        self.assertEqual(response.status_code, 200)

    def test_detail_view_other_user_card_returns_404(self):
        other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        card = LoyaltyCard.objects.create(
            user=other_user,
            store_name='Other Store',
            card_number='123'
        )
        response = self.client.get(f'/loyalty-cards/{card.id}/', follow=True)
        self.assertEqual(response.status_code, 404)

    def test_detail_view_requires_login(self):
        self.client.logout()
        card = LoyaltyCard.objects.create(
            user=self.user,
            store_name='Test Store',
            card_number='123'
        )
        response = self.client.get(f'/loyalty-cards/{card.id}/')
        self.assertIn(response.status_code, [301, 302])

    def test_delete_card_requires_login(self):
        self.client.logout()
        card = LoyaltyCard.objects.create(
            user=self.user,
            store_name='Test Store',
            card_number='123'
        )
        response = self.client.post(f'/loyalty-cards/{card.id}/delete/')
        self.assertIn(response.status_code, [301, 302])