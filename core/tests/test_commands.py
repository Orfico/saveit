# core/tests/test_commands.py
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.management import call_command
from django.utils import timezone
from core.models import Transaction, Category
from decimal import Decimal
from datetime import date
from dateutil.relativedelta import relativedelta
from io import StringIO


class GenerateRecurringTransactionsCommandTest(TestCase):
    """Test generate_recurring_transactions management command"""
    
    def setUp(self):
        """Preliminary setup for tests"""
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create test categories
        self.rent_category = Category.objects.create(
            name='Rent',
            type=Category.EXPENSE,
            user=self.user,
            scope=Category.PERSONAL,
            color='#FF0000'
        )
        
        self.salary_category = Category.objects.create(
            name='Salary',
            type=Category.INCOME,
            user=self.user,
            scope=Category.PERSONAL,
            color='#00FF00'
        )
        
        # Reference date info
        self.today = timezone.now().date()
        self.current_month = self.today.month
        self.current_year = self.today.year

        # Previous month date for recurring transactions
        self.last_month = self.today - relativedelta(months=1)
    
    def test_generates_recurring_expense(self):
        """Test that the command generates a recurring expense transaction"""
        # Create a recurring expense transaction for last month
        recurring_expense = Transaction.objects.create(
            user=self.user,
            category=self.rent_category,
            amount=Decimal('-850.00'),
            description='Monthly Rent',
            date=self.last_month.replace(day=15),
            is_recurring=True
        )

        # Count transactions before running the command
        initial_count = Transaction.objects.count()
        
        # Run the command
        out = StringIO()
        call_command('generate_recurring_transactions', stdout=out)
        
        # Verify that a new transaction was created
        self.assertEqual(Transaction.objects.count(), initial_count + 1)
        
        # Verify that the new transaction is correct
        new_transaction = Transaction.objects.filter(
            description='Monthly Rent',
            is_recurring=False
        ).latest('created_at')
        
        self.assertEqual(new_transaction.amount, Decimal('-850.00'))
        self.assertEqual(new_transaction.category, self.rent_category)
        self.assertEqual(new_transaction.date.month, self.current_month)
        self.assertEqual(new_transaction.date.year, self.current_year)
        self.assertEqual(new_transaction.date.day, 15)
        self.assertFalse(new_transaction.is_recurring)
    
    def test_generates_recurring_income(self):
        """Test that the command generates a recurring income transaction"""
        # Create a recurring income transaction
        recurring_income = Transaction.objects.create(
            user=self.user,
            category=self.salary_category,
            amount=Decimal('2500.00'),  # Positive for income
            description='Monthly Salary',
            date=self.last_month.replace(day=1),
            is_recurring=True
        )

        # Count transactions before running the command
        initial_count = Transaction.objects.count()
        
        # Run the command
        out = StringIO()
        call_command('generate_recurring_transactions', stdout=out)
        
        # Verify that a new transaction was created
        self.assertEqual(Transaction.objects.count(), initial_count + 1)
        
        # Verify that the new transaction maintains the positive sign
        new_transaction = Transaction.objects.filter(
            description='Monthly Salary',
            is_recurring=False
        ).latest('created_at')
        
        self.assertEqual(new_transaction.amount, Decimal('2500.00'))
        self.assertGreater(new_transaction.amount, 0)  # Verify that it is positive
    
    def test_skips_existing_transactions(self):
        """Test that the command skips existing transactions"""
        # Create a recurring transaction
        recurring = Transaction.objects.create(
            user=self.user,
            category=self.rent_category,
            amount=Decimal('-100.00'),
            description='Test Recurring',
            date=self.last_month.replace(day=10),
            is_recurring=True
        )
        
        # Manually create the transaction for the current month to simulate existing (not recurring)
        existing = Transaction.objects.create(
            user=self.user,
            category=self.rent_category,
            amount=Decimal('-100.00'),
            description='Test Recurring',
            date=self.today.replace(day=10),
            is_recurring=False
        )
        
        # Count transactions before running the command
        initial_count = Transaction.objects.count()
        
        # Run the command
        out = StringIO()
        call_command('generate_recurring_transactions', stdout=out)
        output = out.getvalue()
        
        # Verify that NO new transaction was created
        self.assertEqual(Transaction.objects.count(), initial_count)
        
        # Verify that the output contains "Saltata" or "skipped"
        self.assertIn('Saltata', output)
    
    def test_dry_run_does_not_create_transactions(self):
        """Test that the dry-run does not create transactions"""
        # Create a recurring transaction
        recurring = Transaction.objects.create(
            user=self.user,
            category=self.rent_category,
            amount=Decimal('-500.00'),
            description='Dry Run Test',
            date=self.last_month.replace(day=20),
            is_recurring=True
        )

        # Count transactions before running the command
        initial_count = Transaction.objects.count()
        
        # Run the command in dry-run mode
        out = StringIO()
        call_command('generate_recurring_transactions', '--dry-run', stdout=out)
        output = out.getvalue()
        
        # Verify that NO new transaction was created in dry-run mode
        self.assertEqual(Transaction.objects.count(), initial_count)
        
        # Verify that the output contains "DRY-RUN"
        self.assertIn('DRY-RUN', output)
    
    def test_handles_invalid_day_of_month(self):
        """Test that handles invalid days (e.g., Feb 31)"""
        # Create a recurring transaction for the 31st of the month
        recurring = Transaction.objects.create(
            user=self.user,
            category=self.rent_category,
            amount=Decimal('-300.00'),
            description='End of Month',
            date=date(2025, 12, 31),  # 31 december
            is_recurring=True
        )
        
        # If today is February (which has max 28/29 days), 
        # the command should create the transaction for the last day of February
        out = StringIO()
        call_command('generate_recurring_transactions', stdout=out)
        
        # Verify that a transaction was created
        new_transactions = Transaction.objects.filter(
            description='End of Month',
            is_recurring=False,
            date__year=self.current_year,
            date__month=self.current_month
        )
        
        # If we are in February, there should be a transaction
        if self.current_month == 2:
            self.assertEqual(new_transactions.count(), 1)
            # The day should be 28 or 29 (last day of February)
            last_day_of_feb = new_transactions.first().date.day
            self.assertIn(last_day_of_feb, [28, 29])
    
    def test_multiple_recurring_transactions(self):
        """Test that generates multiple recurring transactions correctly"""
        # Create 3 different recurring transactions
        transactions_data = [
            {'amount': Decimal('-850.00'), 'desc': 'Rent', 'day': 1},
            {'amount': Decimal('-50.00'), 'desc': 'Netflix', 'day': 15},
            {'amount': Decimal('3000.00'), 'desc': 'Salary', 'day': 25},
        ]
        
        for data in transactions_data:
            Transaction.objects.create(
                user=self.user,
                category=self.rent_category,
                amount=data['amount'],
                description=data['desc'],
                date=self.last_month.replace(day=data['day']),
                is_recurring=True
            )
        
        # Count transactions before running the command
        initial_count = Transaction.objects.count()
        
        # Run the command
        out = StringIO()
        call_command('generate_recurring_transactions', stdout=out)
        
        # Verify that 3 new transactions were created
        self.assertEqual(Transaction.objects.count(), initial_count + 3)
        
        # Verify that all were created for the current month
        new_transactions = Transaction.objects.filter(
            is_recurring=False,
            date__year=self.current_year,
            date__month=self.current_month
        )
        self.assertEqual(new_transactions.count(), 3)
    
    def test_preserves_amount_sign(self):
        """Test that the sign of the amount is preserved correctly"""
        # Create an expense (negative)
        expense = Transaction.objects.create(
            user=self.user,
            category=self.rent_category,
            amount=Decimal('-100.00'),
            description='Expense Test',
            date=self.last_month.replace(day=5),
            is_recurring=True
        )
        
        # Create an income (positive)
        income = Transaction.objects.create(
            user=self.user,
            category=self.salary_category,
            amount=Decimal('500.00'),
            description='Income Test',
            date=self.last_month.replace(day=10),
            is_recurring=True
        )
        
        # Run the command
        out = StringIO()
        call_command('generate_recurring_transactions', stdout=out)
        
        # Verify the new expense (should be negative)
        new_expense = Transaction.objects.filter(
            description='Expense Test',
            is_recurring=False,
            date__month=self.current_month
        ).first()
        self.assertIsNotNone(new_expense)
        self.assertLess(new_expense.amount, 0)
        self.assertEqual(new_expense.amount, Decimal('-100.00'))
        
        # Verify the new income (should be positive)
        new_income = Transaction.objects.filter(
            description='Income Test',
            is_recurring=False,
            date__month=self.current_month
        ).first()
        self.assertIsNotNone(new_income)
        self.assertGreater(new_income.amount, 0)
        self.assertEqual(new_income.amount, Decimal('500.00'))
    
    def test_command_output_format(self):
        """Test that the command output is formatted correctly"""
        # Create a recurring transaction
        Transaction.objects.create(
            user=self.user,
            category=self.rent_category,
            amount=Decimal('-200.00'),
            description='Test Output',
            date=self.last_month.replace(day=7),
            is_recurring=True
        )
        
        # Run the command and capture the output
        out = StringIO()
        call_command('generate_recurring_transactions', stdout=out)
        output = out.getvalue()
        
        # Verify that the output contains the expected information
        self.assertIn('Generazione transazioni ricorrenti', output)
        self.assertIn('Trovate', output)
        self.assertIn('transazioni ricorrenti', output)
        self.assertIn('Creata', output)
    
    def test_no_recurring_transactions(self):
        """Test the scenario with no recurring transactions"""
        # Create no recurring transactions

        # Run the command
        out = StringIO()
        call_command('generate_recurring_transactions', stdout=out)
        output = out.getvalue()
        
        # Verify that the output indicates 0 recurring transactions found
        self.assertIn('Trovate 0 transazioni ricorrenti', output)
    
    def test_created_transaction_is_not_recurring(self):
        """Test that the created transactions are NOT marked as recurring"""
        # Create a recurring transaction
        Transaction.objects.create(
            user=self.user,
            category=self.rent_category,
            amount=Decimal('-400.00'),
            description='Not Recurring Copy',
            date=self.last_month.replace(day=12),
            is_recurring=True
        )
        
        # Run the command
        out = StringIO()
        call_command('generate_recurring_transactions', stdout=out)
        
        # Verify that the created copy is NOT recurring
        new_transaction = Transaction.objects.filter(
            description='Not Recurring Copy',
            is_recurring=False,
            date__month=self.current_month
        ).first()
        
        self.assertIsNotNone(new_transaction)
        self.assertFalse(new_transaction.is_recurring)
    
    def test_preserves_notes(self):
        """Test that the notes are copied correctly"""
        # Create a recurring transaction with notes
        Transaction.objects.create(
            user=self.user,
            category=self.rent_category,
            amount=Decimal('-150.00'),
            description='With Notes',
            notes='Important note to remember',
            date=self.last_month.replace(day=3),
            is_recurring=True
        )

        # Run the command
        out = StringIO()
        call_command('generate_recurring_transactions', stdout=out)
        
        # Verify that the notes were copied
        new_transaction = Transaction.objects.filter(
            description='With Notes',
            is_recurring=False,
            date__month=self.current_month
        ).first()
        
        self.assertIsNotNone(new_transaction)
        self.assertEqual(new_transaction.notes, 'Important note to remember')


class GenerateRecurringTransactionsMultiUserTest(TestCase):
    """Test the command with multiple users"""
    
    def setUp(self):
        """Preliminary setup for tests with two users"""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='pass123'
        )
        
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='pass123'
        )
        
        self.category1 = Category.objects.create(
            name='Category1',
            type=Category.EXPENSE,
            user=self.user1,
            scope=Category.PERSONAL,
            color='#FF0000'
        )
        
        self.category2 = Category.objects.create(
            name='Category2',
            type=Category.EXPENSE,
            user=self.user2,
            scope=Category.PERSONAL,
            color='#00FF00'
        )
        
        self.today = timezone.now().date()
        self.last_month = self.today - relativedelta(months=1)
    
    def test_generates_for_all_users(self):
        """Test that the command generates transactions for all users"""
        # Create recurring transactions for both users
        Transaction.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal('-100.00'),
            description='User1 Recurring',
            date=self.last_month.replace(day=5),
            is_recurring=True
        )
        
        Transaction.objects.create(
            user=self.user2,
            category=self.category2,
            amount=Decimal('-200.00'),
            description='User2 Recurring',
            date=self.last_month.replace(day=10),
            is_recurring=True
        )
        
        # Count transactions before running the command
        initial_count = Transaction.objects.count()
        
        # Run the command
        out = StringIO()
        call_command('generate_recurring_transactions', stdout=out)
        
        # Verify that 2 new transactions were created (one for each user)
        self.assertEqual(Transaction.objects.count(), initial_count + 2)
        
        # Verify that each user has their transaction
        user1_new = Transaction.objects.filter(
            user=self.user1,
            description='User1 Recurring',
            is_recurring=False
        ).exists()
        
        user2_new = Transaction.objects.filter(
            user=self.user2,
            description='User2 Recurring',
            is_recurring=False
        ).exists()
        
        self.assertTrue(user1_new)
        self.assertTrue(user2_new)