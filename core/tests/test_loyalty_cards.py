# core/tests/test_loyalty_cards.py

import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch, MagicMock
from core.models import LoyaltyCard
from core.utils.barcode_generator import BarcodeGenerator


# ==============================================================================
# MODEL TESTS
# ==============================================================================

class LoyaltyCardModelTest(TestCase):
    """Tests for the LoyaltyCard model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_loyalty_card_creation(self):
        """Test that a loyalty card is created correctly"""
        card = LoyaltyCard.objects.create(
            user=self.user,
            store_name='Test Store',
            card_number='1234567890123',
            barcode_type='ean13',
            notes='Test notes'
        )

        self.assertEqual(card.store_name, 'Test Store')
        self.assertEqual(card.card_number, '1234567890123')
        self.assertEqual(card.barcode_type, 'ean13')
        self.assertEqual(card.notes, 'Test notes')
        self.assertEqual(card.user, self.user)

    def test_loyalty_card_str(self):
        """Test the string representation of a loyalty card"""
        card = LoyaltyCard.objects.create(
            user=self.user,
            store_name='Conad',
            card_number='1234567890123',
            barcode_type='ean13'
        )

        self.assertEqual(str(card), 'Conad - 1234567890123')

    def test_loyalty_card_default_barcode_type(self):
        """Test that default barcode type is code128"""
        card = LoyaltyCard.objects.create(
            user=self.user,
            store_name='Test Store',
            card_number='ABC123'
        )

        self.assertEqual(card.barcode_type, 'code128')

    def test_loyalty_card_ordering(self):
        """Test that cards are ordered by creation date descending"""
        card1 = LoyaltyCard.objects.create(
            user=self.user,
            store_name='Store A',
            card_number='111'
        )
        card2 = LoyaltyCard.objects.create(
            user=self.user,
            store_name='Store B',
            card_number='222'
        )

        cards = LoyaltyCard.objects.filter(user=self.user)
        # Most recent first
        self.assertEqual(cards[0], card2)
        self.assertEqual(cards[1], card1)

    def test_loyalty_card_notes_optional(self):
        """Test that notes field is optional"""
        card = LoyaltyCard.objects.create(
            user=self.user,
            store_name='Test Store',
            card_number='123456789012',
            barcode_type='upca'
        )

        self.assertEqual(card.notes, '')

    def test_loyalty_card_deleted_with_user(self):
        """Test that cards are deleted when user is deleted"""
        LoyaltyCard.objects.create(
            user=self.user,
            store_name='Test Store',
            card_number='123'
        )

        self.assertEqual(LoyaltyCard.objects.count(), 1)
        self.user.delete()
        self.assertEqual(LoyaltyCard.objects.count(), 0)


# ==============================================================================
# BARCODE GENERATOR TESTS
# ==============================================================================

class BarcodeGeneratorTest(TestCase):
    """Tests for the BarcodeGenerator utility"""

    # --- detect_barcode_type ---

    def test_detect_ean13(self):
        """Test detection of EAN-13 (13 digits)"""
        self.assertEqual(BarcodeGenerator.detect_barcode_type('1234567890123'), 'ean13')

    def test_detect_ean8(self):
        """Test detection of EAN-8 (8 digits)"""
        self.assertEqual(BarcodeGenerator.detect_barcode_type('12345678'), 'ean8')

    def test_detect_upca(self):
        """Test detection of UPC-A (12 digits)"""
        self.assertEqual(BarcodeGenerator.detect_barcode_type('123456789012'), 'upca')

    def test_detect_code128_alphanumeric(self):
        """Test detection of Code128 for alphanumeric codes"""
        self.assertEqual(BarcodeGenerator.detect_barcode_type('ABC123'), 'code128')

    def test_detect_code128_odd_length(self):
        """Test detection of Code128 for odd-length numeric codes"""
        self.assertEqual(BarcodeGenerator.detect_barcode_type('12345'), 'code128')

    def test_detect_itf_even_digits(self):
        """Test detection of ITF for even-length numeric codes"""
        self.assertEqual(BarcodeGenerator.detect_barcode_type('1234'), 'itf')

    def test_detect_strips_spaces(self):
        """Test that spaces are stripped before detection"""
        self.assertEqual(BarcodeGenerator.detect_barcode_type(' 1234567890123 '), 'ean13')

    # --- validate_code ---

    def test_validate_ean13_valid(self):
        """Test validation of a valid EAN-13 code"""
        self.assertTrue(BarcodeGenerator.validate_code('1234567890123', 'ean13'))

    def test_validate_ean13_invalid_length(self):
        """Test that EAN-13 with wrong length is invalid"""
        self.assertFalse(BarcodeGenerator.validate_code('12345', 'ean13'))

    def test_validate_ean13_non_numeric(self):
        """Test that EAN-13 with letters is invalid"""
        self.assertFalse(BarcodeGenerator.validate_code('123456789012A', 'ean13'))

    def test_validate_ean8_valid(self):
        """Test validation of a valid EAN-8 code"""
        self.assertTrue(BarcodeGenerator.validate_code('12345678', 'ean8'))

    def test_validate_ean8_invalid(self):
        """Test that EAN-8 with wrong length is invalid"""
        self.assertFalse(BarcodeGenerator.validate_code('1234567', 'ean8'))

    def test_validate_upca_valid(self):
        """Test validation of a valid UPC-A code"""
        self.assertTrue(BarcodeGenerator.validate_code('123456789012', 'upca'))

    def test_validate_upca_invalid(self):
        """Test that UPC-A with wrong length is invalid"""
        self.assertFalse(BarcodeGenerator.validate_code('12345678901', 'upca'))

    def test_validate_itf_valid(self):
        """Test validation of a valid ITF code (even digits)"""
        self.assertTrue(BarcodeGenerator.validate_code('1234', 'itf'))

    def test_validate_itf_invalid_odd(self):
        """Test that ITF with odd length is invalid"""
        self.assertFalse(BarcodeGenerator.validate_code('123', 'itf'))

    def test_validate_code128_any_nonempty(self):
        """Test that Code128 accepts any non-empty string"""
        self.assertTrue(BarcodeGenerator.validate_code('ABC123', 'code128'))
        self.assertTrue(BarcodeGenerator.validate_code('1', 'code128'))

    def test_validate_code128_empty(self):
        """Test that Code128 rejects empty string"""
        self.assertFalse(BarcodeGenerator.validate_code('', 'code128'))

    # --- generate_barcode ---

    def test_generate_barcode_returns_tuple(self):
        """Test that generate_barcode returns a (ContentFile, type) tuple"""
        result = BarcodeGenerator.generate_barcode('ABC123', 'code128')
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_generate_barcode_returns_correct_type(self):
        """Test that generate_barcode returns the correct barcode type"""
        _, barcode_type = BarcodeGenerator.generate_barcode('1234567890123', 'ean13')
        self.assertEqual(barcode_type, 'ean13')

    def test_generate_barcode_autodetect(self):
        """Test that generate_barcode auto-detects type when not provided"""
        _, barcode_type = BarcodeGenerator.generate_barcode('1234567890123')
        self.assertEqual(barcode_type, 'ean13')

    def test_generate_barcode_file_not_empty(self):
        """Test that generated barcode file is not empty"""
        content_file, _ = BarcodeGenerator.generate_barcode('ABC123', 'code128')
        self.assertGreater(len(content_file), 0)

    def test_generate_barcode_invalid_type_falls_back(self):
        """Test that invalid barcode type falls back to code128"""
        _, barcode_type = BarcodeGenerator.generate_barcode('ABC123', 'invalid_type')
        self.assertEqual(barcode_type, 'code128')


# ==============================================================================
# VIEW TESTS
# ==============================================================================

class LoyaltyCardViewTest(TestCase):
    """Tests for loyalty card views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')

    # --- List View ---

    def test_list_view_requires_login(self):
        """Test that list view redirects unauthenticated users"""
        self.client.logout()
        response = self.client.get(reverse('core:loyalty_cards_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_list_view_returns_200(self):
        """Test that list view returns 200 for authenticated users"""
        response = self.client.get(reverse('core:loyalty_cards_list'))
        self.assertEqual(response.status_code, 200)

    def test_list_view_shows_only_user_cards(self):
        """Test that list view shows only the logged-in user's cards"""
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

        response = self.client.get(reverse('core:loyalty_cards_list'))
        cards = response.context['cards']
        self.assertEqual(cards.count(), 1)
        self.assertEqual(cards.first().store_name, 'My Store')

    def test_list_view_empty(self):
        """Test that list view works with no cards"""
        response = self.client.get(reverse('core:loyalty_cards_list'))
        self.assertEqual(response.context['cards'].count(), 0)

    # --- Create View ---

    @patch('core.views.BarcodeGenerator.generate_barcode')
    def test_create_card_success(self, mock_generate):
        """Test successful card creation"""
        # Mock barcode generation to avoid file I/O
        mock_file = MagicMock()
        mock_file.__len__ = lambda self: 100
        mock_generate.return_value = (mock_file, 'ean13')

        data = {
            'store_name': 'Test Store',
            'card_number': '1234567890123',
            'barcode_type': 'ean13',
            'notes': 'Test notes'
        }

        response = self.client.post(
            reverse('core:loyalty_card_create'),
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertTrue(result['success'])
        self.assertEqual(LoyaltyCard.objects.count(), 1)

    def test_create_card_missing_store_name(self):
        """Test that missing store name returns error"""
        data = {
            'store_name': '',
            'card_number': '1234567890123',
            'barcode_type': 'ean13'
        }

        response = self.client.post(
            reverse('core:loyalty_card_create'),
            data=json.dumps(data),
            content_type='application/json'
        )

        result = json.loads(response.content)
        self.assertFalse(result['success'])
        self.assertEqual(LoyaltyCard.objects.count(), 0)

    def test_create_card_missing_card_number(self):
        """Test that missing card number returns error"""
        data = {
            'store_name': 'Test Store',
            'card_number': '',
            'barcode_type': 'code128'
        }

        response = self.client.post(
            reverse('core:loyalty_card_create'),
            data=json.dumps(data),
            content_type='application/json'
        )

        result = json.loads(response.content)
        self.assertFalse(result['success'])

    def test_create_card_requires_login(self):
        """Test that create view requires authentication"""
        self.client.logout()
        data = {
            'store_name': 'Test Store',
            'card_number': '123',
            'barcode_type': 'code128'
        }

        response = self.client.post(
            reverse('core:loyalty_card_create'),
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(LoyaltyCard.objects.count(), 0)

    # --- Detail View ---

    def test_detail_view_returns_200(self):
        """Test that detail view returns 200 for card owner"""
        card = LoyaltyCard.objects.create(
            user=self.user,
            store_name='Test Store',
            card_number='123'
        )

        response = self.client.get(
            reverse('core:loyalty_card_detail', args=[card.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_view_other_user_card_returns_404(self):
        """Test that detail view returns 404 for another user's card"""
        other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        card = LoyaltyCard.objects.create(
            user=other_user,
            store_name='Other Store',
            card_number='123'
        )

        response = self.client.get(
            reverse('core:loyalty_card_detail', args=[card.id])
        )
        self.assertEqual(response.status_code, 404)

    def test_detail_view_requires_login(self):
        """Test that detail view requires authentication"""
        self.client.logout()
        card = LoyaltyCard.objects.create(
            user=self.user,
            store_name='Test Store',
            card_number='123'
        )

        response = self.client.get(
            reverse('core:loyalty_card_detail', args=[card.id])
        )
        self.assertEqual(response.status_code, 302)

    # --- Delete View ---

    def test_delete_card_success(self):
        """Test successful card deletion"""
        card = LoyaltyCard.objects.create(
            user=self.user,
            store_name='Test Store',
            card_number='123'
        )

        self.assertEqual(LoyaltyCard.objects.count(), 1)

        response = self.client.post(
            reverse('core:loyalty_card_delete', args=[card.id])
        )

        result = json.loads(response.content)
        self.assertTrue(result['success'])
        self.assertEqual(LoyaltyCard.objects.count(), 0)

    def test_delete_other_user_card_returns_404(self):
        """Test that deleting another user's card returns 404"""
        other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        card = LoyaltyCard.objects.create(
            user=other_user,
            store_name='Other Store',
            card_number='123'
        )

        response = self.client.post(
            reverse('core:loyalty_card_delete', args=[card.id])
        )

        result = json.loads(response.content)
        self.assertFalse(result['success'])
        # Card should still exist
        self.assertEqual(LoyaltyCard.objects.count(), 1)

    def test_delete_card_requires_login(self):
        """Test that delete view requires authentication"""
        self.client.logout()
        card = LoyaltyCard.objects.create(
            user=self.user,
            store_name='Test Store',
            card_number='123'
        )

        response = self.client.post(
            reverse('core:loyalty_card_delete', args=[card.id])
        )

        self.assertEqual(response.status_code, 302)
        # Card should still exist
        self.assertEqual(LoyaltyCard.objects.count(), 1)

    def test_delete_nonexistent_card(self):
        """Test that deleting a non-existent card returns 404"""
        response = self.client.post(
            reverse('core:loyalty_card_delete', args=[9999])
        )

        result = json.loads(response.content)
        self.assertFalse(result['success'])