# core/tests/test_commands.py
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from core.models import Category, Transaction

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _master_date_for_monthly():
    """Return a date such that master + 1 month is always <= today."""
    today = timezone.now().date()
    return today - timedelta(days=35)   # +1 month lands ~5 days in the past


def _run(extra_args=()):
    out = StringIO()
    call_command('generate_recurring_transactions', *extra_args, stdout=out)
    return out.getvalue()


# ---------------------------------------------------------------------------
# Single-user tests
# ---------------------------------------------------------------------------

class GenerateRecurringTransactionsCommandTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', email='test@example.com', password='testpass123'
        )
        self.rent_cat = Category.objects.create(
            name='Rent', type=Category.EXPENSE, user=self.user, scope=Category.PERSONAL,
        )
        self.salary_cat = Category.objects.create(
            name='Salary', type=Category.INCOME, user=self.user, scope=Category.PERSONAL,
        )
        self.today = timezone.now().date()

    # ---- monthly ----

    def test_generates_monthly_expense(self):
        master_date = _master_date_for_monthly()
        Transaction.objects.create(
            user=self.user, category=self.rent_cat,
            amount=Decimal('-850.00'), description='Monthly Rent',
            date=master_date, is_recurring=True,
            recurrence_interval=Transaction.MONTHLY,
        )
        initial = Transaction.objects.count()
        _run()
        self.assertEqual(Transaction.objects.count(), initial + 1)
        copy = Transaction.objects.filter(description='Monthly Rent', is_recurring=False).latest('created_at')
        expected_date = master_date + relativedelta(months=1)
        self.assertEqual(copy.date, expected_date)
        self.assertFalse(copy.is_recurring)

    def test_generates_monthly_income(self):
        master_date = _master_date_for_monthly()
        Transaction.objects.create(
            user=self.user, category=self.salary_cat,
            amount=Decimal('2500.00'), description='Monthly Salary',
            date=master_date, is_recurring=True,
            recurrence_interval=Transaction.MONTHLY,
        )
        initial = Transaction.objects.count()
        _run()
        self.assertEqual(Transaction.objects.count(), initial + 1)
        copy = Transaction.objects.filter(description='Monthly Salary', is_recurring=False).latest('created_at')
        self.assertGreater(copy.amount, 0)
        self.assertEqual(copy.amount, Decimal('2500.00'))

    def test_skips_existing_monthly_copy(self):
        master_date = _master_date_for_monthly()
        Transaction.objects.create(
            user=self.user, category=self.rent_cat,
            amount=Decimal('-100.00'), description='Test Recurring',
            date=master_date, is_recurring=True,
            recurrence_interval=Transaction.MONTHLY,
        )
        copy_date = master_date + relativedelta(months=1)
        Transaction.objects.create(
            user=self.user, category=self.rent_cat,
            amount=Decimal('-100.00'), description='Test Recurring',
            date=copy_date, is_recurring=False,
        )
        initial = Transaction.objects.count()
        output = _run()
        self.assertEqual(Transaction.objects.count(), initial)
        self.assertIn('Skipped', output)

    # ---- weekly ----

    def test_generates_weekly_copy(self):
        master_date = self.today - timedelta(days=8)   # next occurrence = today - 1 day
        Transaction.objects.create(
            user=self.user, category=self.rent_cat,
            amount=Decimal('-50.00'), description='Weekly Gym',
            date=master_date, is_recurring=True,
            recurrence_interval=Transaction.WEEKLY,
        )
        initial = Transaction.objects.count()
        _run()
        self.assertGreater(Transaction.objects.count(), initial)
        copy = Transaction.objects.filter(description='Weekly Gym', is_recurring=False).first()
        self.assertIsNotNone(copy)
        self.assertEqual(copy.date, master_date + timedelta(days=7))

    def test_generates_multiple_weekly_copies_when_behind(self):
        """If the command hasn't run for >1 week, it catches up."""
        master_date = self.today - timedelta(days=22)  # 3 weeks ago
        Transaction.objects.create(
            user=self.user, category=self.rent_cat,
            amount=Decimal('-20.00'), description='Weekly Coffee',
            date=master_date, is_recurring=True,
            recurrence_interval=Transaction.WEEKLY,
        )
        _run()
        copies = Transaction.objects.filter(description='Weekly Coffee', is_recurring=False)
        self.assertGreaterEqual(copies.count(), 3)

    # ---- annually ----

    def test_generates_annual_copy(self):
        master_date = self.today - relativedelta(years=1) - timedelta(days=1)
        Transaction.objects.create(
            user=self.user, category=self.salary_cat,
            amount=Decimal('500.00'), description='Annual Bonus',
            date=master_date, is_recurring=True,
            recurrence_interval=Transaction.ANNUALLY,
        )
        initial = Transaction.objects.count()
        _run()
        self.assertGreater(Transaction.objects.count(), initial)
        copy = Transaction.objects.filter(description='Annual Bonus', is_recurring=False).first()
        self.assertIsNotNone(copy)
        self.assertEqual(copy.date, master_date + relativedelta(years=1))

    # ---- custom ----

    def test_generates_custom_interval_copy(self):
        interval_days = 10
        master_date = self.today - timedelta(days=interval_days + 1)
        Transaction.objects.create(
            user=self.user, category=self.rent_cat,
            amount=Decimal('-30.00'), description='Custom Interval',
            date=master_date, is_recurring=True,
            recurrence_interval=Transaction.CUSTOM, recurrence_days=interval_days,
        )
        initial = Transaction.objects.count()
        _run()
        self.assertGreater(Transaction.objects.count(), initial)
        copy = Transaction.objects.filter(description='Custom Interval', is_recurring=False).first()
        self.assertIsNotNone(copy)
        self.assertEqual(copy.date, master_date + timedelta(days=interval_days))

    # ---- dry run ----

    def test_dry_run_does_not_create_transactions(self):
        master_date = _master_date_for_monthly()
        Transaction.objects.create(
            user=self.user, category=self.rent_cat,
            amount=Decimal('-500.00'), description='Dry Run Test',
            date=master_date, is_recurring=True,
        )
        initial = Transaction.objects.count()
        output = _run(['--dry-run'])
        self.assertEqual(Transaction.objects.count(), initial)
        self.assertIn('DRY-RUN', output)

    # ---- misc ----

    def test_no_recurring_transactions(self):
        output = _run()
        self.assertIn('No recurring transactions found', output)

    def test_created_copy_is_not_recurring(self):
        master_date = _master_date_for_monthly()
        Transaction.objects.create(
            user=self.user, category=self.rent_cat,
            amount=Decimal('-400.00'), description='Not Recurring Copy',
            date=master_date, is_recurring=True,
        )
        _run()
        copy = Transaction.objects.filter(description='Not Recurring Copy', is_recurring=False).first()
        self.assertIsNotNone(copy)
        self.assertFalse(copy.is_recurring)

    def test_preserves_amount_sign(self):
        master_date = _master_date_for_monthly()
        Transaction.objects.create(
            user=self.user, category=self.rent_cat,
            amount=Decimal('-100.00'), description='Expense Sign',
            date=master_date, is_recurring=True,
        )
        Transaction.objects.create(
            user=self.user, category=self.salary_cat,
            amount=Decimal('500.00'), description='Income Sign',
            date=master_date, is_recurring=True,
        )
        _run()
        expense = Transaction.objects.filter(description='Expense Sign', is_recurring=False).first()
        income = Transaction.objects.filter(description='Income Sign', is_recurring=False).first()
        self.assertLess(expense.amount, 0)
        self.assertGreater(income.amount, 0)

    def test_preserves_notes(self):
        master_date = _master_date_for_monthly()
        Transaction.objects.create(
            user=self.user, category=self.rent_cat,
            amount=Decimal('-150.00'), description='With Notes',
            notes='Important note', date=master_date, is_recurring=True,
        )
        _run()
        copy = Transaction.objects.filter(description='With Notes', is_recurring=False).first()
        self.assertIsNotNone(copy)
        self.assertEqual(copy.notes, 'Important note')

    def test_handles_end_of_month_clamp(self):
        """relativedelta gracefully clamps end-of-month dates; no exception raised."""
        # Pre-fill copies from Jan through last month so the command only tries the current month
        master = Transaction.objects.create(
            user=self.user, category=self.rent_cat,
            amount=Decimal('-300.00'), description='End of Month',
            date=date(2025, 12, 31), is_recurring=True,
        )
        try:
            _run()
        except Exception as exc:
            self.fail(f'Command raised an exception for end-of-month date: {exc}')
        copies = Transaction.objects.filter(description='End of Month', is_recurring=False)
        self.assertGreater(copies.count(), 0)

    def test_multiple_recurring_transactions(self):
        master_date = _master_date_for_monthly()
        for desc in ('Rent', 'Netflix', 'Salary'):
            Transaction.objects.create(
                user=self.user, category=self.rent_cat,
                amount=Decimal('-100.00'), description=desc,
                date=master_date, is_recurring=True,
            )
        initial = Transaction.objects.count()
        _run()
        self.assertEqual(Transaction.objects.count(), initial + 3)

    def test_command_output_contains_summary(self):
        master_date = _master_date_for_monthly()
        Transaction.objects.create(
            user=self.user, category=self.rent_cat,
            amount=Decimal('-200.00'), description='Test Output',
            date=master_date, is_recurring=True,
        )
        output = _run()
        self.assertIn('Generating recurring transactions', output)
        self.assertIn('Found', output)
        self.assertIn('Created', output)


# ---------------------------------------------------------------------------
# Multi-user tests
# ---------------------------------------------------------------------------

class GenerateRecurringTransactionsMultiUserTest(TestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='pass')
        self.user2 = User.objects.create_user(username='user2', password='pass')
        self.cat1 = Category.objects.create(
            name='Cat1', type=Category.EXPENSE, user=self.user1, scope=Category.PERSONAL,
        )
        self.cat2 = Category.objects.create(
            name='Cat2', type=Category.EXPENSE, user=self.user2, scope=Category.PERSONAL,
        )

    def test_generates_for_all_users(self):
        master_date = _master_date_for_monthly()
        Transaction.objects.create(
            user=self.user1, category=self.cat1,
            amount=Decimal('-100.00'), description='User1 Recurring',
            date=master_date, is_recurring=True,
        )
        Transaction.objects.create(
            user=self.user2, category=self.cat2,
            amount=Decimal('-200.00'), description='User2 Recurring',
            date=master_date, is_recurring=True,
        )
        initial = Transaction.objects.count()
        _run()
        self.assertEqual(Transaction.objects.count(), initial + 2)
        self.assertTrue(Transaction.objects.filter(
            user=self.user1, description='User1 Recurring', is_recurring=False).exists())
        self.assertTrue(Transaction.objects.filter(
            user=self.user2, description='User2 Recurring', is_recurring=False).exists())
