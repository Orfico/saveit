# core/tests/test_views.py
import json
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
    
    def test_search_in_category_name(self):
        """Search should find transactions by category name"""
        url = reverse('core:transaction_list') + '?search=transport'
        response = self.client.get(url, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bus ticket')
    
    def test_search_no_results(self):
        url = reverse('core:transaction_list') + '?search=nonexistent'
        response = self.client.get(url, follow=True)
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


class RecurringTransactionDeleteViewTest(TestCase):
    """Tests for the recurring transaction delete endpoint"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='deluser', password='pass')
        self.category = Category.objects.create(
            name='Rent', type=Category.EXPENSE, user=self.user, scope=Category.PERSONAL
        )
        # Master created in the past
        self.master = Transaction.objects.create(
            user=self.user, category=self.category,
            amount=Decimal('-800.00'), date=date.today() - timedelta(days=60),
            description='Monthly rent', is_recurring=True,
        )
        # Past copy (60 days ago) – must NOT be deleted
        self.past_copy = Transaction.objects.create(
            user=self.user, category=self.category,
            amount=Decimal('-800.00'), date=date.today() - timedelta(days=30),
            description='Monthly rent', is_recurring=False,
        )
        # Future copy (30 days from now) – may be deleted
        self.future_copy = Transaction.objects.create(
            user=self.user, category=self.category,
            amount=Decimal('-800.00'), date=date.today() + timedelta(days=30),
            description='Monthly rent', is_recurring=False,
        )
        self.client.login(username='deluser', password='pass')
        self.url = reverse('core:recurring_transaction_delete', args=[self.master.pk])

    def _delete(self, delete_copies):
        return self.client.post(
            self.url,
            data=json.dumps({'delete_copies': delete_copies}),
            content_type='application/json',
        )

    def test_delete_without_copies_preserves_master_as_regular_transaction(self):
        """Removing a recurring transaction should convert the master to a regular transaction, not delete it."""
        response = self._delete(False)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)['success'])
        master = Transaction.objects.get(pk=self.master.pk)
        self.assertFalse(master.is_recurring)

    def test_delete_without_copies_keeps_past_and_future_copies(self):
        """Without delete_copies, existing generated copies must be untouched."""
        self._delete(False)
        self.assertTrue(Transaction.objects.filter(pk=self.past_copy.pk).exists())
        self.assertTrue(Transaction.objects.filter(pk=self.future_copy.pk).exists())

    def test_delete_with_copies_removes_only_future_copies(self):
        """With delete_copies=True, only future copies (date > today) should be removed."""
        self._delete(True)
        self.assertTrue(Transaction.objects.filter(pk=self.past_copy.pk).exists())
        self.assertFalse(Transaction.objects.filter(pk=self.future_copy.pk).exists())

    def test_delete_with_copies_preserves_master_as_regular_transaction(self):
        """Even with delete_copies=True, the master itself must survive as a regular transaction."""
        self._delete(True)
        master = Transaction.objects.get(pk=self.master.pk)
        self.assertFalse(master.is_recurring)


class RecurringTransactionUpdateViewTest(TestCase):
    """Tests for the recurring transaction update endpoint"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='upduser', password='pass')
        self.category = Category.objects.create(
            name='Rent', type=Category.EXPENSE, user=self.user, scope=Category.PERSONAL
        )
        self.master = Transaction.objects.create(
            user=self.user, category=self.category,
            amount=Decimal('-800.00'), date=date.today() - timedelta(days=60),
            description='Monthly rent', is_recurring=True,
        )
        # Past copy – must NOT be updated
        self.past_copy = Transaction.objects.create(
            user=self.user, category=self.category,
            amount=Decimal('-800.00'), date=date.today() - timedelta(days=30),
            description='Monthly rent', is_recurring=False,
        )
        # Future copy – may be updated
        self.future_copy = Transaction.objects.create(
            user=self.user, category=self.category,
            amount=Decimal('-800.00'), date=date.today() + timedelta(days=30),
            description='Monthly rent', is_recurring=False,
        )
        self.client.login(username='upduser', password='pass')
        self.url = reverse('core:recurring_transaction_update', args=[self.master.pk])

    def _update(self, update_copies, extra=None):
        payload = {
            'description': 'Monthly rent', 'amount': -900.00,
            'category_id': self.category.pk, 'notes': '',
            'update_copies': update_copies,
        }
        if extra:
            payload.update(extra)
        return self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_update_without_copies_does_not_touch_past_or_future_copies(self):
        """Without update_copies, generated copies must remain unchanged."""
        self._update(False)
        self.past_copy.refresh_from_db()
        self.future_copy.refresh_from_db()
        self.assertEqual(self.past_copy.amount, Decimal('-800.00'))
        self.assertEqual(self.future_copy.amount, Decimal('-800.00'))

    def test_update_with_copies_does_not_affect_past_copies(self):
        """With update_copies=True, past copies (date <= today) must be untouched."""
        self._update(True)
        self.past_copy.refresh_from_db()
        self.assertEqual(self.past_copy.amount, Decimal('-800.00'))

    def test_update_with_copies_updates_future_copies(self):
        """With update_copies=True, future copies (date > today) must be updated."""
        self._update(True)
        self.future_copy.refresh_from_db()
        self.assertEqual(self.future_copy.amount, Decimal('-900.00'))

    def test_update_saves_recurrence_interval(self):
        """recurrence_interval is persisted when sent in the payload."""
        self._update(False, extra={'recurrence_interval': 'weekly'})
        self.master.refresh_from_db()
        self.assertEqual(self.master.recurrence_interval, 'weekly')

    def test_update_saves_recurrence_days_for_custom(self):
        """recurrence_days is persisted when interval is custom."""
        self._update(False, extra={'recurrence_interval': 'custom', 'recurrence_days': 14})
        self.master.refresh_from_db()
        self.assertEqual(self.master.recurrence_interval, 'custom')
        self.assertEqual(self.master.recurrence_days, 14)

    def test_update_clears_recurrence_days_for_non_custom(self):
        """recurrence_days is cleared when interval changes away from custom."""
        self.master.recurrence_interval = 'custom'
        self.master.recurrence_days = 14
        self.master.save()
        self._update(False, extra={'recurrence_interval': 'monthly', 'recurrence_days': None})
        self.master.refresh_from_db()
        self.assertIsNone(self.master.recurrence_days)


class CategoryViewTest(TestCase):
    """Tests for the categories list and create views (standard accounts)"""

    def setUp(self):
        self.user = User.objects.create_user(username='catuser', password='pass')
        self.client.login(username='catuser', password='pass')

    def test_categories_list_renders(self):
        response = self.client.get(reverse('core:categories_list'))
        self.assertEqual(response.status_code, 200)

    def test_create_expense_category(self):
        response = self.client.post(
            reverse('core:category_create'),
            {'name': 'Groceries', 'type': 'EX', 'color': '#ff0000'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Category.objects.filter(name='Groceries', user=self.user, type=Category.EXPENSE).exists())

    def test_create_income_category(self):
        self.client.post(
            reverse('core:category_create'),
            {'name': 'Freelance', 'type': 'IN', 'color': '#00ff00'},
            follow=True,
        )
        self.assertTrue(Category.objects.filter(name='Freelance', user=self.user, type=Category.INCOME).exists())

    def test_create_category_requires_name(self):
        self.client.post(
            reverse('core:category_create'),
            {'name': '', 'type': 'EX', 'color': '#ff0000'},
            follow=True,
        )
        self.assertEqual(Category.objects.filter(user=self.user).count(), 0)

    def test_create_duplicate_category_does_not_duplicate(self):
        Category.objects.create(name='Food', type=Category.EXPENSE, user=self.user, scope='PERSONAL')
        self.client.post(
            reverse('core:category_create'),
            {'name': 'Food', 'type': 'EX', 'color': '#aabbcc'},
            follow=True,
        )
        self.assertEqual(Category.objects.filter(name='Food', user=self.user).count(), 1)

    def test_categories_list_shows_both_types(self):
        Category.objects.create(name='Salary', type=Category.INCOME, user=self.user, scope='PERSONAL')
        Category.objects.create(name='Rent', type=Category.EXPENSE, user=self.user, scope='PERSONAL')
        response = self.client.get(reverse('core:categories_list'))
        self.assertContains(response, 'Salary')
        self.assertContains(response, 'Rent')

    # ── Edit category ────────────────────────────────────────────────────────

    def _make_cat(self, name='Food', cat_type=Category.EXPENSE):
        return Category.objects.create(
            name=name, type=cat_type, user=self.user, scope='PERSONAL', color='#ff0000'
        )

    def test_edit_category_updates_name_and_color(self):
        cat = self._make_cat()
        response = self.client.post(
            reverse('core:category_edit', args=[cat.pk]),
            {'name': 'Groceries', 'color': '#00ff00'},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        cat.refresh_from_db()
        self.assertEqual(cat.name, 'Groceries')
        self.assertEqual(cat.color, '#00ff00')

    def test_edit_category_empty_name_rejected(self):
        cat = self._make_cat()
        response = self.client.post(
            reverse('core:category_edit', args=[cat.pk]),
            {'name': '', 'color': '#ff0000'},
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])
        cat.refresh_from_db()
        self.assertEqual(cat.name, 'Food')

    def test_edit_category_duplicate_name_rejected(self):
        cat1 = self._make_cat('Food')
        cat2 = self._make_cat('Groceries')
        response = self.client.post(
            reverse('core:category_edit', args=[cat2.pk]),
            {'name': 'Food', 'color': '#ff0000'},
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])

    def test_edit_category_wrong_owner_returns_404(self):
        other = User.objects.create_user(username='other', password='pass')
        cat = Category.objects.create(
            name='Other', type=Category.EXPENSE, user=other, scope='PERSONAL'
        )
        response = self.client.post(
            reverse('core:category_edit', args=[cat.pk]),
            {'name': 'Hacked', 'color': '#000000'},
        )
        self.assertEqual(response.status_code, 404)
        cat.refresh_from_db()
        self.assertEqual(cat.name, 'Other')

    def test_edit_global_category_returns_404(self):
        global_cat = Category.objects.create(
            name='Utilities', type=Category.EXPENSE, user=None, scope=Category.GLOBAL
        )
        response = self.client.post(
            reverse('core:category_edit', args=[global_cat.pk]),
            {'name': 'Hacked', 'color': '#000000'},
        )
        self.assertEqual(response.status_code, 404)