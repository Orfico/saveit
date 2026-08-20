# core/tests/test_loyalty_cards.py

import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
from django.core.files.base import ContentFile
from core.models import LoyaltyCard, FamilyProfile, FamilyMember
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


class LoyaltyCardFamilySharingTest(TestCase):

    def setUp(self):
        self.family_user = User.objects.create_user(
            username='familyuser', password='pass'
        )
        self.fp = FamilyProfile.objects.create(
            user=self.family_user, member_1='Mario', member_2='Lucia'
        )
        self.member_user = User.objects.create_user(
            username='memberuser', password='pass'
        )
        FamilyMember.objects.create(
            family_profile=self.fp, user=self.member_user
        )
        self.unrelated_user = User.objects.create_user(
            username='stranger', password='pass'
        )

    def _make_card(self, user, store='Store', shared=False):
        return LoyaltyCard.objects.create(
            user=user, store_name=store, card_number='123',
            shared_with_family=shared,
        )

    # ── Model field ──────────────────────────────────────────────────

    def test_shared_with_family_defaults_to_false(self):
        card = LoyaltyCard.objects.create(
            user=self.family_user, store_name='S', card_number='1'
        )
        self.assertFalse(card.shared_with_family)

    # ── Toggle sharing endpoint ──────────────────────────────────────

    def test_toggle_sharing_on(self):
        card = self._make_card(self.family_user, shared=False)
        self.client.login(username='familyuser', password='pass')
        resp = self.client.post(f'/loyalty-cards/{card.id}/toggle-sharing/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['shared'])
        card.refresh_from_db()
        self.assertTrue(card.shared_with_family)

    def test_toggle_sharing_off(self):
        card = self._make_card(self.family_user, shared=True)
        self.client.login(username='familyuser', password='pass')
        resp = self.client.post(f'/loyalty-cards/{card.id}/toggle-sharing/')
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertFalse(data['shared'])
        card.refresh_from_db()
        self.assertFalse(card.shared_with_family)

    def test_toggle_sharing_non_owner_returns_404(self):
        card = self._make_card(self.family_user, shared=False)
        self.client.login(username='memberuser', password='pass')
        resp = self.client.post(f'/loyalty-cards/{card.id}/toggle-sharing/')
        self.assertEqual(resp.status_code, 404)
        card.refresh_from_db()
        self.assertFalse(card.shared_with_family)

    def test_toggle_sharing_requires_login(self):
        card = self._make_card(self.family_user)
        resp = self.client.post(f'/loyalty-cards/{card.id}/toggle-sharing/')
        self.assertIn(resp.status_code, [301, 302])

    # ── List view – family member sees shared cards ──────────────────

    def test_member_sees_shared_family_card_in_list(self):
        self._make_card(self.family_user, store='Shared Store', shared=True)
        self.client.login(username='memberuser', password='pass')
        resp = self.client.get('/loyalty-cards/', follow=True)
        cards = list(resp.context['cards'])
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].store_name, 'Shared Store')

    def test_member_does_not_see_unshared_family_card(self):
        self._make_card(self.family_user, store='Private', shared=False)
        self.client.login(username='memberuser', password='pass')
        resp = self.client.get('/loyalty-cards/', follow=True)
        self.assertEqual(list(resp.context['cards']), [])

    def test_family_user_sees_shared_member_card(self):
        self._make_card(self.member_user, store='Member Card', shared=True)
        self.client.login(username='familyuser', password='pass')
        resp = self.client.get('/loyalty-cards/', follow=True)
        cards = list(resp.context['cards'])
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].store_name, 'Member Card')

    def test_unrelated_user_does_not_see_shared_card(self):
        self._make_card(self.family_user, store='Shared', shared=True)
        self.client.login(username='stranger', password='pass')
        resp = self.client.get('/loyalty-cards/', follow=True)
        self.assertEqual(list(resp.context['cards']), [])

    def test_own_cards_always_visible(self):
        self._make_card(self.family_user, store='Own', shared=False)
        self.client.login(username='familyuser', password='pass')
        resp = self.client.get('/loyalty-cards/', follow=True)
        cards = list(resp.context['cards'])
        self.assertEqual(len(cards), 1)

    def test_list_no_duplicate_when_own_card_shared(self):
        self._make_card(self.family_user, store='Mine', shared=True)
        self.client.login(username='familyuser', password='pass')
        resp = self.client.get('/loyalty-cards/', follow=True)
        cards = list(resp.context['cards'])
        self.assertEqual(len(cards), 1)

    # ── Detail view – family member can view shared card ─────────────

    def test_member_can_view_shared_card_detail(self):
        card = self._make_card(self.family_user, store='Shared', shared=True)
        self.client.login(username='memberuser', password='pass')
        resp = self.client.get(f'/loyalty-cards/{card.id}/', follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['is_owner'])

    def test_member_cannot_view_unshared_card_detail(self):
        card = self._make_card(self.family_user, store='Private', shared=False)
        self.client.login(username='memberuser', password='pass')
        resp = self.client.get(f'/loyalty-cards/{card.id}/', follow=True)
        self.assertEqual(resp.status_code, 404)

    def test_unrelated_user_cannot_view_shared_card_detail(self):
        card = self._make_card(self.family_user, store='Shared', shared=True)
        self.client.login(username='stranger', password='pass')
        resp = self.client.get(f'/loyalty-cards/{card.id}/', follow=True)
        self.assertEqual(resp.status_code, 404)

    def test_detail_context_is_owner_true_for_owner(self):
        card = self._make_card(self.family_user, store='Mine', shared=True)
        self.client.login(username='familyuser', password='pass')
        resp = self.client.get(f'/loyalty-cards/{card.id}/', follow=True)
        self.assertTrue(resp.context['is_owner'])

    # ── Delete – only owner can delete ───────────────────────────────

    def test_member_cannot_delete_shared_card(self):
        card = self._make_card(self.family_user, store='Shared', shared=True)
        self.client.login(username='memberuser', password='pass')
        resp = self.client.post(f'/loyalty-cards/{card.id}/delete/')
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(LoyaltyCard.objects.filter(pk=card.pk).exists())