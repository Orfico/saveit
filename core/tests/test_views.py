# core/tests/test_views.py
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from core.models import Transaction, Category
from decimal import Decimal
from datetime import date, timedelta
import json


class CategoryDeleteViewTest(TestCase):
    """Category delete view tests"""
    
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
        
        self.category_empty = Category.objects.create(
            name='Empty Category',
            type=Category.EXPENSE,
            user=self.user,
            scope=Category.PERSONAL
        )
        
        self.category_with_transactions = Category.objects.create(
            name='Category with Transactions',
            type=Category.EXPENSE,
            user=self.user,
            scope=Category.PERSONAL
        )
        
        # Create a transaction for the category
        Transaction.objects.create(
            user=self.user,
            category=self.category_with_transactions,
            amount=Decimal('-50.00'),
            date=date.today(),
            description='Test transaction'
        )
        
        self.client.login(username='testuser', password='testpass123')
    
    def test_delete_empty_category_success(self):
        """Delete category with no transactions should succeed"""
        url = reverse('core:category_delete', kwargs={'pk': self.category_empty.pk})
        response = self.client.post(url, follow=True)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertFalse(Category.objects.filter(pk=self.category_empty.pk).exists())
    
    def test_delete_category_with_transactions_fails(self):
        """Delete category with transactions should fail"""
        url = reverse('core:category_delete', kwargs={'pk': self.category_with_transactions.pk})
        response = self.client.post(url, follow=True)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertTrue(Category.objects.filter(pk=self.category_with_transactions.pk).exists())
    
    def test_delete_other_user_category_returns_404(self):
        """Deleting another user's category should return 404"""
        other_category = Category.objects.create(
            name='Other User Category',
            type=Category.EXPENSE,
            user=self.other_user,
            scope=Category.PERSONAL
        )
        
        url = reverse('core:category_delete', kwargs={'pk': other_category.pk})
        response = self.client.post(url, follow=True)
        
        self.assertEqual(response.status_code, 404)


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


class RecurringTransactionUpdateViewTest(TestCase):
    """Recurring transaction update tests"""
    
    def setUp(self):
        """Setup test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.category = Category.objects.create(
            name='Rent',
            type=Category.EXPENSE,
            user=self.user,
            scope=Category.PERSONAL
        )
        
        # Create recurring master
        self.master = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('-800.00'),
            date=date(2025, 1, 1),
            description='Monthly rent',
            is_recurring=True
        )
        
        # Create future copy
        self.future_copy = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('-800.00'),
            date=date.today() + timedelta(days=30),
            description='Monthly rent',
            is_recurring=False
        )
        
        self.client.login(username='testuser', password='testpass123')
    
    def test_update_only_master(self):
        """Update without update_copies should only update master"""
        url = reverse('core:recurring_transaction_update', kwargs={'pk': self.master.pk})
        data = {
            'amount': -900.00,
            'description': 'Updated rent',
            'category_id': self.category.id,
            'update_copies': False
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json',
            follow=True
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Master should be updated
        self.master.refresh_from_db()
        self.assertEqual(self.master.amount, Decimal('-900.00'))
        self.assertEqual(self.master.description, 'Updated rent')
        
        # Copy should NOT be updated
        self.future_copy.refresh_from_db()
        self.assertEqual(self.future_copy.amount, Decimal('-800.00'))
        self.assertEqual(self.future_copy.description, 'Monthly rent')
    
    def test_update_master_and_copies(self):
        """Update with update_copies should update master and future copies"""
        url = reverse('core:recurring_transaction_update', kwargs={'pk': self.master.pk})
        data = {
            'amount': -900.00,
            'description': 'Updated rent',
            'category_id': self.category.id,
            'notes': 'New notes',
            'update_copies': True
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json',
            follow=True
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Master should be updated
        self.master.refresh_from_db()
        self.assertEqual(self.master.amount, Decimal('-900.00'))
        
        # Future copy should be updated
        self.future_copy.refresh_from_db()
        self.assertEqual(self.future_copy.amount, Decimal('-900.00'))
        self.assertEqual(self.future_copy.description, 'Updated rent')


class RecurringTransactionDeleteViewTest(TestCase):
    """Recurring transaction delete tests"""
    
    def setUp(self):
        """Setup test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.category = Category.objects.create(
            name='Subscription',
            type=Category.EXPENSE,
            user=self.user,
            scope=Category.PERSONAL
        )
        
        # Create recurring master
        self.master = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('-9.99'),
            date=date(2025, 1, 1),
            description='Netflix',
            is_recurring=True
        )
        
        # Create future copy
        self.future_copy = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('-9.99'),
            date=date.today() + timedelta(days=30),
            description='Netflix',
            is_recurring=False
        )
        
        self.client.login(username='testuser', password='testpass123')
    
    def test_delete_only_master(self):
        """Delete without delete_copies should only delete master"""
        url = reverse('core:recurring_transaction_delete', kwargs={'pk': self.master.pk})
        data = {'delete_copies': False}
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json',
            follow=True
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Master should be deleted
        self.assertFalse(Transaction.objects.filter(pk=self.master.pk).exists())
        
        # Copy should still exist
        self.assertTrue(Transaction.objects.filter(pk=self.future_copy.pk).exists())
    
    def test_delete_master_and_copies(self):
        """Delete with delete_copies should delete master and future copies"""
        url = reverse('core:recurring_transaction_delete', kwargs={'pk': self.master.pk})
        data = {'delete_copies': True}
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json',
            follow=True
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Master should be deleted
        self.assertFalse(Transaction.objects.filter(pk=self.master.pk).exists())
        
        # Future copy should be deleted
        self.assertFalse(Transaction.objects.filter(pk=self.future_copy.pk).exists())