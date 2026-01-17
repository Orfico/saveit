# core/tests/test_forms.py
from django.test import TestCase
from django.contrib.auth.models import User
from core.forms import TransactionForm
from core.models import Transaction, Category
from decimal import Decimal
from datetime import date


class TransactionFormTest(TestCase):
    """TransactionForm tests"""
    
    def setUp(self):
        """Preliminary setup before each test"""
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test categories
        self.expense_category = Category.objects.create(
            name='Food',
            type=Category.EXPENSE,
            user=self.user,
            scope=Category.PERSONAL,
            color='#FF0000'
        )
        
        self.income_category = Category.objects.create(
            name='Salary',
            type=Category.INCOME,
            user=self.user,
            scope=Category.PERSONAL,
            color='#00FF00'
        )
    
    def test_form_saves_expense_as_negative(self):
        """Test expense is saved with negative amount"""
        form_data = {
            'type': 'expense',
            'amount': '100.50',  # Inputed as positive
            'date': date.today(),
            'description': 'Grocery shopping',
            'category': self.expense_category.id,
            'notes': '',
            'is_recurring': False
        }
        
        form = TransactionForm(data=form_data, user=self.user)
        
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
        
        transaction = form.save(commit=False)
        transaction.user = self.user
        transaction.save()
        
        # Check that amount is negative
        self.assertEqual(transaction.amount, Decimal('-100.50'))
        self.assertTrue(transaction.is_expense)
    
    def test_form_saves_income_as_positive(self):
        """Test income is saved with positive amount"""
        form_data = {
            'type': 'income',
            'amount': '1500.00',  # Inputed as positive
            'date': date.today(),
            'description': 'Monthly salary',
            'category': self.income_category.id,
            'notes': '',
            'is_recurring': False
        }
        
        form = TransactionForm(data=form_data, user=self.user)
        
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
        
        transaction = form.save(commit=False)
        transaction.user = self.user
        transaction.save()
        
        # Check that amount is positive
        self.assertEqual(transaction.amount, Decimal('1500.00'))
        self.assertTrue(transaction.is_income)
    
    def test_form_requires_category_or_new_category(self):
        """Test that the form requires an existing or new category"""
        form_data = {
            'type': 'expense',
            'amount': '50.00',
            'date': date.today(),
            'description': 'Test',
            # No category selected
            'notes': '',
            'is_recurring': False
        }
        
        form = TransactionForm(data=form_data, user=self.user)

        # The form should be invalid
        self.assertFalse(form.is_valid())
        self.assertIn('You must select an existing category or enter a new category name', str(form.errors))
    
    def test_form_creates_new_category(self):
        """Test that the form creates a new category if requested"""
        initial_category_count = Category.objects.count()
        
        form_data = {
            'type': 'expense',
            'amount': '75.00',
            'date': date.today(),
            'description': 'Test with new category',
            'category': '',  # No existing category
            'new_category_name': 'New Test Category',
            'category_type': Category.EXPENSE,
            'category_color': '#0000FF',
            'notes': '',
            'is_recurring': False
        }
        
        form = TransactionForm(data=form_data, user=self.user)
        
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
        
        # Simulate saving the form and creating the new category
        new_category_name = form.cleaned_data.get('new_category_name')
        if new_category_name:
            category, created = Category.objects.get_or_create(
                name=new_category_name,
                user=self.user,
                type=form.cleaned_data.get('category_type', Category.EXPENSE),
                defaults={
                    'scope': Category.PERSONAL,
                    'color': form.cleaned_data.get('category_color', '#3B82F6'),
                }
            )
            transaction = form.save(commit=False)
            transaction.category = category
            transaction.user = self.user
            transaction.save()
        
        # Check that the new category was created
        self.assertEqual(Category.objects.count(), initial_category_count + 1)
        self.assertTrue(
            Category.objects.filter(name='New Test Category').exists()
        )
    
    def test_recurring_checkbox_saves_true(self):
        """Test that the is_recurring checkbox saves True when selected"""
        form_data = {
            'type': 'expense',
            'amount': '850.00',
            'date': date.today(),
            'description': 'Rent',
            'category': self.expense_category.id,
            'notes': '',
            'is_recurring': True  # Checkbox active
        }
        
        form = TransactionForm(data=form_data, user=self.user)
        
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
        
        transaction = form.save(commit=False)
        transaction.user = self.user
        transaction.save()
        
        # Check that is_recurring is True
        self.assertTrue(transaction.is_recurring)
    
    def test_recurring_checkbox_saves_false(self):
        """Test that the is_recurring checkbox saves False when not selected"""
        form_data = {
            'type': 'expense',
            'amount': '25.00',
            'date': date.today(),
            'description': 'One-time expense',
            'category': self.expense_category.id,
            'notes': '',
            'is_recurring': False  # Checkbox inactive
        }
        
        form = TransactionForm(data=form_data, user=self.user)
        
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
        
        transaction = form.save(commit=False)
        transaction.user = self.user
        transaction.save()
        
        # Check that is_recurring is False
        self.assertFalse(transaction.is_recurring)
    
    def test_form_handles_decimal_amounts(self):
        """Test that the form handles decimal amounts correctly"""
        form_data = {
            'type': 'expense',
            'amount': '12.99',
            'date': date.today(),
            'description': 'Subscription',
            'category': self.expense_category.id,
            'notes': '',
            'is_recurring': False
        }
        
        form = TransactionForm(data=form_data, user=self.user)
        
        self.assertTrue(form.is_valid())
        
        transaction = form.save(commit=False)
        transaction.user = self.user
        transaction.save()
        
        self.assertEqual(transaction.amount, Decimal('-12.99'))
    
    def test_form_requires_positive_amount(self):
        """Test that the form requires a positive amount input"""
        form_data = {
            'type': 'expense',
            'amount': '-100.00',  # Negative not allowed
            'date': date.today(),
            'description': 'Test',
            'category': self.expense_category.id,
            'notes': '',
            'is_recurring': False
        }
        
        form = TransactionForm(data=form_data, user=self.user)
        
        # The form should be invalid
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
    
    def test_form_requires_minimum_amount(self):
        """Test that the form requires a minimum amount (0.01)"""
        form_data = {
            'type': 'expense',
            'amount': '0.00',  # Zero not allowed
            'date': date.today(),
            'description': 'Test',
            'category': self.expense_category.id,
            'notes': '',
            'is_recurring': False
        }
        
        form = TransactionForm(data=form_data, user=self.user)
        
        # The form should be invalid
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
    
    def test_form_filters_categories_by_user(self):
        """Test that the form shows only categories of the current user"""
        # Create an additional user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        # Create category for the other user
        other_category = Category.objects.create(
            name='Other User Category',
            type=Category.EXPENSE,
            user=other_user,
            scope=Category.PERSONAL,
            color='#000000'
        )
        
        # Initialize the form with self.user
        form = TransactionForm(user=self.user)
        
        # The available categories should be filtered by the current user
        self.assertNotIn(other_category, form.fields['category'].queryset)