# core/tests/test_views.py
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from core.models import Transaction, Category
from decimal import Decimal
from datetime import date, timedelta


class TransactionSearchViewTest(TestCase):
    """Transaction search tests"""
    
    def setUp(self):
        """Setup test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.category_food = Category.objects.create(
            name='Food',
            type=Category.EXPENSE,
            user=self.user,
            scope=Category.PERSONAL
        )
        
        self.category_transport = Category.objects.create(
            name='Transport',
            type=Category.EXPENSE,
            user=self.user,
            scope=Category.PERSONAL
        )
        
        # Create test transactions
        Transaction.objects.create(
            user=self.user,
            category=self.category_food,
            amount=Decimal('-20.00'),
            date=date.today(),
            description='Pizza dinner',
            notes='With friends'
        )
        
        Transaction.objects.create(
            user=self.user,
            category=self.category_transport,
            amount=Decimal('-15.00'),
            date=date.today(),
            description='Bus ticket',
            notes='Monthly pass'
        )
        
        self.client.login(username='testuser', password='testpass123')
    
    def test_search_in_description(self):
        """Search should find transactions by description"""
        url = reverse('core:transaction_list') + '?search=pizza'
        response = self.client.get(url, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pizza dinner')
        self.assertNotContains(response, 'Bus ticket')
    
    def test_search_in_notes(self):
        """Search should find transactions by notes"""
        url = reverse('core:transaction_list') + '?search=friends'
        response = self.client.get(url, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pizza dinner')
    
    def test_search_in_category_name(self):
        """Search should find transactions by category name"""
        url = reverse('core:transaction_list') + '?search=transport'
        response = self.client.get(url, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bus ticket')
    
    def test_search_no_results(self):
        """Search with no matches should return empty"""
        url = reverse('core:transaction_list') + '?search=nonexistent'
        response = self.client.get(url, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Pizza dinner')
        self.assertNotContains(response, 'Bus ticket')


class RecurringTransactionsViewTest(TestCase):
    """Recurring transactions view tests"""
    
    def setUp(self):
        """Setup test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        
        self.category = Category.objects.create(
            name='Rent',
            type=Category.EXPENSE,
            user=self.user,
            scope=Category.PERSONAL
        )
        
        # Create recurring transaction
        self.recurring = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('-800.00'),
            date=date.today(),
            description='Monthly rent',
            is_recurring=True
        )
        
        # Create other user's recurring
        other_category = Category.objects.create(
            name='Other Rent',
            type=Category.EXPENSE,
            user=self.other_user,
            scope=Category.PERSONAL
        )
        
        Transaction.objects.create(
            user=self.other_user,
            category=other_category,
            amount=Decimal('-500.00'),
            date=date.today(),
            description='Other rent',
            is_recurring=True
        )
        
        self.client.login(username='testuser', password='testpass123')
    
    def test_shows_user_recurring_transactions(self):
        """View should show user's recurring transactions"""
        url = reverse('core:recurring_transactions')
        response = self.client.get(url, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Monthly rent')
    
    def test_does_not_show_other_user_recurring(self):
        """View should not show other users' recurring transactions"""
        url = reverse('core:recurring_transactions')
        response = self.client.get(url, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Other rent')