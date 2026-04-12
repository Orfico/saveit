# core/tests/test_csv.py

import io
import csv
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import Category, Transaction


def make_user(username='csvuser', password='pass'):
    return User.objects.create_user(username=username, password=password)


def make_category(user, name='Food', cat_type='EX'):
    return Category.objects.create(
        name=name, type=cat_type, user=user, scope='PERSONAL', color='#ff0000'
    )


def make_transaction(user, category, amount, date, description=''):
    return Transaction.objects.create(
        user=user, category=category, amount=amount, date=date, description=description
    )


def build_csv(rows):
    """Costruisce un file CSV in memoria dalle righe fornite."""
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=['date', 'description', 'amount', 'category', 'notes', 'is_recurring']
    )
    writer.writeheader()
    writer.writerows(rows)
    buf.seek(0)
    return io.BytesIO(buf.read().encode('utf-8'))


class ExportCSVTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.login(username='csvuser', password='pass')
        cat = make_category(self.user)
        year = timezone.now().year
        make_transaction(self.user, cat, -100, f'{year}-01-10', 'spesa A')
        make_transaction(self.user, cat, -200, f'{year}-02-10', 'spesa B')

    def test_export_returns_csv(self):
        response = self.client.get(reverse('core:transactions_export'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_export_contains_all_transactions(self):
        response = self.client.get(reverse('core:transactions_export'))
        content = response.content.decode('utf-8')
        self.assertIn('spesa A', content)
        self.assertIn('spesa B', content)

    def test_export_respects_date_filter(self):
        year = timezone.now().year
        response = self.client.get(
            reverse('core:transactions_export'),
            {'date_from': f'{year}-02-01', 'date_to': f'{year}-02-28'},
        )
        content = response.content.decode('utf-8')
        self.assertIn('spesa B', content)
        self.assertNotIn('spesa A', content)


class ImportCSVTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.login(username='csvuser', password='pass')
        self.cat = make_category(self.user, 'Food', 'EX')

    def test_import_creates_transactions(self):
        csv_file = build_csv([{
            'date': '2025-03-01', 'description': 'test import',
            'amount': '-50', 'category': 'Food', 'notes': '', 'is_recurring': 'False',
        }])
        self.client.post(
            reverse('core:transactions_import'),
            {'csv_file': csv_file},
        )
        self.assertTrue(
            Transaction.objects.filter(user=self.user, description='test import').exists()
        )

    def test_import_skips_duplicates(self):
        make_transaction(self.user, self.cat, -50, '2025-03-01', 'duplicato')
        csv_file = build_csv([{
            'date': '2025-03-01', 'description': 'duplicato',
            'amount': '-50', 'category': 'Food', 'notes': '', 'is_recurring': 'False',
        }])
        self.client.post(
            reverse('core:transactions_import'),
            {'csv_file': csv_file},
        )
        count = Transaction.objects.filter(user=self.user, description='duplicato').count()
        self.assertEqual(count, 1)

    def test_import_rejects_non_csv(self):
        fake_file = io.BytesIO(b'not a csv file')
        fake_file.name = 'data.txt'
        response = self.client.post(
            reverse('core:transactions_import'),
            {'csv_file': fake_file},
            follow=True,
        )
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 0)