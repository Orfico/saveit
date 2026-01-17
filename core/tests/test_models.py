# core/tests/test_models.py
from django.test import TestCase
from django.contrib.auth.models import User
from core.models import Transaction, Category
from decimal import Decimal
from datetime import date


class TransactionModelTest(TestCase):
    """Transaction model tests"""
    
    def setUp(self):
        """Preliminary setup before each test"""
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create a test category
        self.category = Category.objects.create(
            name='Test Category',
            type=Category.EXPENSE,
            user=self.user,
            scope=Category.PERSONAL,
            color='#FF0000'
        )
    
    def test_expense_has_negative_amount(self):
        """Test expenses have negative amount"""
        transaction = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('-100.50'),  # Expense
            description='Test Expense',
            date=date.today(),
            is_recurring=False
        )
        
        self.assertLess(transaction.amount, 0)
        self.assertEqual(transaction.amount, Decimal('-100.50'))
    
    def test_income_has_positive_amount(self):
        """Test incomes have positive amount"""
        transaction = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('500.00'),  # Income
            description='Test Income',
            date=date.today(),
            is_recurring=False
        )
        
        self.assertGreater(transaction.amount, 0)
        self.assertEqual(transaction.amount, Decimal('500.00'))
    
    def test_is_income_property(self):
        """Test is_income property"""
        # Test with income
        income = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('1000.00'),
            description='Salary',
            date=date.today()
        )
        self.assertTrue(income.is_income)
        
        # Test with expense
        expense = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('-50.00'),
            description='Groceries',
            date=date.today()
        )
        self.assertFalse(expense.is_income)
    
    def test_is_expense_property(self):
        """Test is_expense property"""
        # Test with expense
        expense = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('-75.25'),
            description='Transport',
            date=date.today()
        )
        self.assertTrue(expense.is_expense)
        
        # Test with income
        income = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('2000.00'),
            description='Bonus',
            date=date.today()
        )
        self.assertFalse(income.is_expense)
    
    def test_amount_abs_property(self):
        """Test amount_abs property returns absolute value"""
        # Test with expense (negative)
        expense = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('-123.45'),
            description='Bill',
            date=date.today()
        )
        self.assertEqual(expense.amount_abs, Decimal('123.45'))
        
        # Test with income (positive)
        income = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('678.90'),
            description='Payment',
            date=date.today()
        )
        self.assertEqual(income.amount_abs, Decimal('678.90'))
    
    def test_display_amount_income(self):
        """Test dislay_amount formatting for incomes"""
        income = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('1500.00'),
            description='Salary',
            date=date.today()
        )
        
        self.assertEqual(income.display_amount, '+€1500.00')
    
    def test_display_amount_expense(self):
        """Test display_amount formatting for expenses"""
        expense = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('-85.50'),
            description='Dinner',
            date=date.today()
        )
        
        self.assertEqual(expense.display_amount, '-€85.50')
    
    def test_display_amount_with_decimals(self):
        """Test display_amount is displayed correctly with two places decimal formatting"""
        # Amount with one decimal place
        transaction = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('-10.5'),
            description='Coffee',
            date=date.today()
        )
        
        self.assertEqual(transaction.display_amount, '-€10.50')
        
        # Amount without decimals
        transaction2 = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('100'),
            description='Gift',
            date=date.today()
        )
        
        self.assertEqual(transaction2.display_amount, '+€100.00')
    
    def test_recurring_transaction_flag(self):
        """Test is_recurring flag is saved and retrieved correctly"""
        # Recurring transaction
        recurring = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('-850.00'),
            description='Rent',
            date=date.today(),
            is_recurring=True
        )
        self.assertTrue(recurring.is_recurring)
        
        # Non-recurring transaction
        normal = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('-20.00'),
            description='One-time expense',
            date=date.today(),
            is_recurring=False
        )
        self.assertFalse(normal.is_recurring)
    
    def test_transaction_str_representation(self):
        """Test Transaction model string representation"""
        transaction = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('-50.00'),
            description='Test Transaction',
            date=date(2026, 1, 15)
        )
        
        expected = f"{self.category.name}: €{transaction.amount} ({transaction.date})"
        self.assertEqual(str(transaction), expected)
    
    def test_transaction_ordering(self):
        """Test transactions ordering by date descending"""
        # Create multiple transactions with different dates
        t1 = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('-10.00'),
            description='Oldest',
            date=date(2026, 1, 1)
        )
        
        t2 = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('-20.00'),
            description='Newest',
            date=date(2026, 1, 15)
        )
        
        t3 = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('-30.00'),
            description='Middle',
            date=date(2026, 1, 10)
        )
        
        # Retrieve all transactions and check order (descending by date)
        transactions = list(Transaction.objects.all())
        
        self.assertEqual(transactions[0].description, 'Newest')
        self.assertEqual(transactions[1].description, 'Middle')
        self.assertEqual(transactions[2].description, 'Oldest')


class CategoryModelTest(TestCase):
    """Category model tests"""
    
    def setUp(self):
        """Preliminary setup before each test"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_personal_category_creation(self):
        """Test creation personal category"""
        category = Category.objects.create(
            name='My Category',
            type=Category.EXPENSE,
            user=self.user,
            scope=Category.PERSONAL,
            color='#00FF00'
        )
        
        self.assertEqual(category.name, 'My Category')
        self.assertEqual(category.type, Category.EXPENSE)
        self.assertEqual(category.scope, Category.PERSONAL)
        self.assertEqual(category.user, self.user)
    
    def test_category_str_representation(self):
        """Test Category model string representation"""
        category = Category.objects.create(
            name='Food',
            type=Category.EXPENSE,
            user=self.user,
            scope=Category.PERSONAL,
            color='#FF5733'
        )

        self.assertIn('Food', str(category))
        self.assertIn('Expense', str(category))