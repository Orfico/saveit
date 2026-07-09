from datetime import date
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db.models.signals import post_save
from django.test import TestCase

from core.models import Category, FamilyMember, FamilyProfile, Transaction
from core.signals import propagate_family_transaction


# ── helpers ──────────────────────────────────────────────────────────────────

def make_user(username):
    return User.objects.create_user(username=username, password='pass')


def make_family_user(username):
    user = make_user(username)
    FamilyProfile.objects.create(user=user, member_1='Alice', member_2='Bob')
    return user


def make_category(user, name='Food', cat_type=Category.EXPENSE):
    return Category.objects.create(
        name=name, user=user, type=cat_type,
        scope=Category.PERSONAL, color='#FF0000',
    )


def make_transaction(user, category, amount, description='Lunch', target_date=None):
    return Transaction.objects.create(
        user=user,
        category=category,
        amount=Decimal(str(amount)),
        date=target_date or date(2026, 6, 15),
        description=description,
        notes='test note',
        is_recurring=False,
        paid_by=Transaction.MEMBER_1,
    )


def run_command(*args, **kwargs):
    out = StringIO()
    call_command('distribute_family_transactions', *args, stdout=out, **kwargs)
    return out.getvalue()


TODAY = date(2026, 6, 15)
TODAY_STR = '2026-06-15'


# ── tests ────────────────────────────────────────────────────────────────────

class DistributeFamilyTransactionsTest(TestCase):

    def setUp(self):
        # Disconnect the post_save signal so manual make_transaction() calls
        # don't auto-propagate and interfere with command-under-test assertions.
        post_save.disconnect(propagate_family_transaction, sender=Transaction)

        self.family = make_family_user('family')
        self.member_a = make_user('member_a')
        self.member_b = make_user('member_b')
        FamilyMember.objects.create(family_profile=self.family.family_profile, user=self.member_a)
        FamilyMember.objects.create(family_profile=self.family.family_profile, user=self.member_b)
        self.cat_family = make_category(self.family, 'Food')

    def tearDown(self):
        post_save.connect(propagate_family_transaction, sender=Transaction)

    # ── basic distribution ────────────────────────────────────────────────

    def test_transaction_created_for_each_member(self):
        make_transaction(self.family, self.cat_family, -10, target_date=TODAY)
        run_command('--date', TODAY_STR)
        self.assertEqual(Transaction.objects.filter(user=self.member_a).count(), 1)
        self.assertEqual(Transaction.objects.filter(user=self.member_b).count(), 1)

    def test_amount_is_halved(self):
        make_transaction(self.family, self.cat_family, -10, target_date=TODAY)
        run_command('--date', TODAY_STR)
        txn = Transaction.objects.get(user=self.member_a)
        self.assertEqual(txn.amount, Decimal('-5.00'))

    def test_amount_is_halved_for_odd_cents(self):
        make_transaction(self.family, self.cat_family, -7, target_date=TODAY)
        run_command('--date', TODAY_STR)
        txn = Transaction.objects.get(user=self.member_a)
        # 7 / 2 = 3.5 → -3.50
        self.assertEqual(txn.amount, Decimal('-3.50'))

    def test_description_and_notes_inherited(self):
        make_transaction(self.family, self.cat_family, -10, description='Pizza night', target_date=TODAY)
        run_command('--date', TODAY_STR)
        txn = Transaction.objects.get(user=self.member_a)
        self.assertEqual(txn.description, 'Pizza night')
        self.assertEqual(txn.notes, 'test note')

    def test_paid_by_is_none_on_copies(self):
        make_transaction(self.family, self.cat_family, -10, target_date=TODAY)
        run_command('--date', TODAY_STR)
        txn = Transaction.objects.get(user=self.member_a)
        self.assertIsNone(txn.paid_by)

    def test_is_recurring_false_on_copies(self):
        txn = make_transaction(self.family, self.cat_family, -10, target_date=TODAY)
        txn.is_recurring = True
        txn.save()
        run_command('--date', TODAY_STR)
        copy = Transaction.objects.get(user=self.member_a)
        self.assertFalse(copy.is_recurring)

    def test_original_transaction_unchanged(self):
        original = make_transaction(self.family, self.cat_family, -10, target_date=TODAY)
        run_command('--date', TODAY_STR)
        original.refresh_from_db()
        self.assertEqual(original.amount, Decimal('-10'))
        self.assertEqual(original.user, self.family)

    # ── multiple transactions ─────────────────────────────────────────────

    def test_multiple_transactions_all_distributed(self):
        make_transaction(self.family, self.cat_family, -10, description='T1', target_date=TODAY)
        make_transaction(self.family, self.cat_family, -20, description='T2', target_date=TODAY)
        run_command('--date', TODAY_STR)
        self.assertEqual(Transaction.objects.filter(user=self.member_a).count(), 2)

    # ── edge cases ────────────────────────────────────────────────────────

    def test_no_transactions_today_produces_no_copies(self):
        run_command('--date', TODAY_STR)
        self.assertEqual(Transaction.objects.filter(user=self.member_a).count(), 0)

    def test_no_members_produces_no_copies(self):
        FamilyMember.objects.all().delete()
        make_transaction(self.family, self.cat_family, -10, target_date=TODAY)
        run_command('--date', TODAY_STR)
        self.assertEqual(Transaction.objects.filter(user=self.member_a).count(), 0)

    def test_no_family_profiles_exits_cleanly(self):
        FamilyProfile.objects.all().delete()
        output = run_command('--date', TODAY_STR)
        self.assertIn('No family profiles', output)

    def test_transactions_from_other_dates_are_not_distributed(self):
        make_transaction(self.family, self.cat_family, -10, target_date=date(2026, 6, 14))
        run_command('--date', TODAY_STR)
        self.assertEqual(Transaction.objects.filter(user=self.member_a).count(), 0)

    # ── deduplication ─────────────────────────────────────────────────────

    def test_duplicate_not_created_on_second_run(self):
        make_transaction(self.family, self.cat_family, -10, target_date=TODAY)
        run_command('--date', TODAY_STR)
        run_command('--date', TODAY_STR)
        self.assertEqual(Transaction.objects.filter(user=self.member_a).count(), 1)

    def test_duplicate_skipped_count_reported(self):
        make_transaction(self.family, self.cat_family, -10, target_date=TODAY)
        run_command('--date', TODAY_STR)
        output = run_command('--date', TODAY_STR)
        self.assertIn('SKIP', output)

    # ── category resolution ───────────────────────────────────────────────

    def test_category_resolved_from_member_own_categories(self):
        member_cat = make_category(self.member_a, 'Food')
        make_transaction(self.family, self.cat_family, -10, target_date=TODAY)
        run_command('--date', TODAY_STR)
        txn = Transaction.objects.get(user=self.member_a)
        self.assertEqual(txn.category, member_cat)

    def test_category_auto_created_if_missing(self):
        make_transaction(self.family, self.cat_family, -10, target_date=TODAY)
        self.assertEqual(Category.objects.filter(user=self.member_a).count(), 0)
        run_command('--date', TODAY_STR)
        self.assertTrue(Category.objects.filter(user=self.member_a, name='Food').exists())

    def test_global_category_reused(self):
        global_cat = Category.objects.create(
            name='Food', type=Category.EXPENSE, scope=Category.GLOBAL, color='#00FF00'
        )
        make_transaction(self.family, self.cat_family, -10, target_date=TODAY)
        run_command('--date', TODAY_STR)
        txn = Transaction.objects.get(user=self.member_a)
        self.assertEqual(txn.category, global_cat)
        # No personal category auto-created
        self.assertFalse(Category.objects.filter(user=self.member_a).exists())

    # ── dry-run ───────────────────────────────────────────────────────────

    def test_dry_run_creates_nothing(self):
        make_transaction(self.family, self.cat_family, -10, target_date=TODAY)
        run_command('--date', TODAY_STR, dry_run=True)
        self.assertEqual(Transaction.objects.filter(user=self.member_a).count(), 0)

    def test_dry_run_output_mentions_dry_run(self):
        make_transaction(self.family, self.cat_family, -10, target_date=TODAY)
        output = run_command('--date', TODAY_STR, dry_run=True)
        self.assertIn('DRY-RUN', output)

    # ── --date flag ───────────────────────────────────────────────────────

    def test_custom_date_flag(self):
        other_date = date(2026, 1, 1)
        make_transaction(self.family, self.cat_family, -10, target_date=other_date)
        run_command('--date', '2026-01-01')
        self.assertEqual(Transaction.objects.filter(user=self.member_a).count(), 1)

    def test_invalid_date_raises_error(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            call_command('distribute_family_transactions', '--date', 'not-a-date', stdout=StringIO())

    # ── multiple family profiles ──────────────────────────────────────────

    def test_multiple_family_profiles_all_processed(self):
        family2 = make_family_user('family2')
        member_c = make_user('member_c')
        FamilyMember.objects.create(family_profile=family2.family_profile, user=member_c)
        cat2 = make_category(family2, 'Travel')

        make_transaction(self.family, self.cat_family, -10, target_date=TODAY)
        make_transaction(family2, cat2, -20, target_date=TODAY)

        run_command('--date', TODAY_STR)

        self.assertEqual(Transaction.objects.filter(user=self.member_a).count(), 1)
        self.assertEqual(Transaction.objects.filter(user=member_c).count(), 1)
        self.assertEqual(Transaction.objects.get(user=member_c).amount, Decimal('-10.00'))
