# core/tests/test_family.py

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from core.models import Category, FamilyProfile, Transaction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username='user', password='pass'):
    return User.objects.create_user(username=username, password=password)


def make_family_user(username='family', password='pass', m1='Mario', m2='Lucia'):
    user = make_user(username, password)
    FamilyProfile.objects.create(user=user, member_1=m1, member_2=m2)
    return user


def make_category(user, name='Food', cat_type='EX'):
    return Category.objects.create(
        name=name, type=cat_type, user=user, scope='PERSONAL', color='#ff0000'
    )


# ===========================================================================
# FamilyProfile model
# ===========================================================================

class FamilyProfileModelTest(TestCase):

    def test_family_profile_created_with_correct_names(self):
        user = make_family_user()
        fp = user.family_profile
        self.assertEqual(fp.member_1, 'Mario')
        self.assertEqual(fp.member_2, 'Lucia')

    def test_member_name_helper(self):
        user = make_family_user()
        fp = user.family_profile
        self.assertEqual(fp.member_name('member_1'), 'Mario')
        self.assertEqual(fp.member_name('member_2'), 'Lucia')

    def test_standard_user_has_no_family_profile(self):
        user = make_user()
        self.assertFalse(hasattr(user, 'family_profile'))


# ===========================================================================
# Registration
# ===========================================================================

class FamilyRegistrationTest(TestCase):

    def test_register_family_account_creates_profile(self):
        self.client.post(reverse('core:register'), {
            'username': 'newfamily',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'is_family_account': 'on',
            'member_1': 'Mario',
            'member_2': 'Lucia',
        })
        user = User.objects.get(username='newfamily')
        self.assertTrue(hasattr(user, 'family_profile'))
        self.assertEqual(user.family_profile.member_1, 'Mario')

    def test_register_standard_account_has_no_profile(self):
        self.client.post(reverse('core:register'), {
            'username': 'standard',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })
        user = User.objects.get(username='standard')
        self.assertFalse(hasattr(user, 'family_profile'))


# ===========================================================================
# Dashboard — family context
# ===========================================================================

class FamilyDashboardTest(TestCase):

    def setUp(self):
        self.user = make_family_user()
        self.client.login(username='family', password='pass')
        self.cat = make_category(self.user)
        Transaction.objects.create(
            user=self.user, category=self.cat,
            amount=-100, date='2026-01-10',
            description='spesa Mario', paid_by=Transaction.MEMBER_1,
        )
        Transaction.objects.create(
            user=self.user, category=self.cat,
            amount=-60, date='2026-01-15',
            description='spesa Lucia', paid_by=Transaction.MEMBER_2,
        )

    def test_dashboard_returns_200(self):
        response = self.client.get(reverse('core:dashboard'), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_family_context_flag(self):
        response = self.client.get(reverse('core:dashboard'), follow=True)
        self.assertTrue(response.context['is_family'])

    def test_balance_calculation(self):
        """Mario ha pagato 100, Lucia 60 → totale 160 → quota 80 → Lucia deve 20 a Mario."""
        response = self.client.get(reverse('core:dashboard'), follow=True)
        ctx = response.context
        self.assertAlmostEqual(ctx['m1_total'], 100.0)
        self.assertAlmostEqual(ctx['m2_total'], 60.0)
        self.assertAlmostEqual(ctx['fair_share'], 80.0)
        self.assertAlmostEqual(ctx['debt'], 20.0)
        self.assertEqual(ctx['debtor'], 'Lucia')
        self.assertEqual(ctx['creditor'], 'Mario')


# ===========================================================================
# Transaction — paid_by field
# ===========================================================================

class FamilyTransactionTest(TestCase):

    def setUp(self):
        self.user = make_family_user()
        self.client.login(username='family', password='pass')
        self.cat = make_category(self.user)

    def test_paid_by_stored_correctly(self):
        t = Transaction.objects.create(
            user=self.user, category=self.cat,
            amount=-50, date='2026-01-10',
            paid_by=Transaction.MEMBER_1,
        )
        self.assertEqual(t.paid_by, 'member_1')

    def test_standard_transaction_has_no_paid_by(self):
        std_user = make_user('std', 'pass')
        cat = make_category(std_user)
        t = Transaction.objects.create(
            user=std_user, category=cat, amount=-50, date='2026-01-10'
        )
        self.assertIsNone(t.paid_by)