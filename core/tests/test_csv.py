# core/tests/test_csv.py

import io
import csv
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
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


def build_csv(rows, include_id=False):
    """Costruisce un SimpleUploadedFile CSV dalle righe fornite."""
    fieldnames = ['date', 'description', 'amount', 'category', 'notes', 'is_recurring']
    if include_id:
        fieldnames = ['id'] + fieldnames
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return SimpleUploadedFile(
        name='transactions.csv',
        content=buf.getvalue().encode('utf-8'),
        content_type='text/csv',
    )


class ExportCSVTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.login(username='csvuser', password='pass')
        cat = make_category(self.user)
        year = timezone.now().year
        make_transaction(self.user, cat, -100, f'{year}-01-10', 'spesa A')
        make_transaction(self.user, cat, -200, f'{year}-02-10', 'spesa B')

    def test_export_returns_csv(self):
        response = self.client.get(reverse('core:transactions_export'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_export_contains_id_column(self):
        response = self.client.get(reverse('core:transactions_export'), follow=True)
        content = response.content.decode('utf-8')
        first_line = content.splitlines()[0]
        self.assertTrue(first_line.startswith('id,'))

    def test_export_contains_all_transactions(self):
        response = self.client.get(reverse('core:transactions_export'), follow=True)
        content = response.content.decode('utf-8')
        self.assertIn('spesa A', content)
        self.assertIn('spesa B', content)

    def test_export_respects_date_filter(self):
        year = timezone.now().year
        response = self.client.get(
            reverse('core:transactions_export'),
            {'date_from': f'{year}-02-01', 'date_to': f'{year}-02-28'},
            follow=True,
        )
        content = response.content.decode('utf-8')
        self.assertIn('spesa B', content)
        self.assertNotIn('spesa A', content)


class ImportCSVTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.login(username='csvuser', password='pass')
        self.cat = make_category(self.user, 'Food', 'EX')

    def test_import_creates_new_transaction(self):
        csv_file = build_csv([{
            'date': '2025-05-01', 'description': 'nuova spesa',
            'amount': '-75', 'category': 'Food', 'notes': '', 'is_recurring': 'False',
        }])
        self.client.post(reverse('core:transactions_import'), {'csv_file': csv_file})
        self.assertTrue(Transaction.objects.filter(user=self.user, description='nuova spesa').exists())

    def test_import_skips_duplicates(self):
        make_transaction(self.user, self.cat, -50, '2025-03-01', 'duplicato')
        csv_file = build_csv([{
            'date': '2025-03-01', 'description': 'duplicato',
            'amount': '-50', 'category': 'Food', 'notes': '', 'is_recurring': 'False',
        }])
        self.client.post(reverse('core:transactions_import'), {'csv_file': csv_file})
        count = Transaction.objects.filter(user=self.user, description='duplicato').count()
        self.assertEqual(count, 1)

    def test_import_rejects_non_csv(self):
        fake_file = SimpleUploadedFile(
            name='data.txt', content=b'not a csv file', content_type='text/plain',
        )
        self.client.post(reverse('core:transactions_import'), {'csv_file': fake_file})
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 0)

    def test_import_updates_existing_by_id(self):
        t = make_transaction(self.user, self.cat, -50, '2025-03-01', 'originale')
        csv_file = build_csv([{
            'id': str(t.pk),
            'date': '2025-03-01', 'description': 'aggiornata',
            'amount': '-80', 'category': 'Food', 'notes': 'nota', 'is_recurring': 'False',
        }], include_id=True)
        self.client.post(reverse('core:transactions_import'), {'csv_file': csv_file})
        t.refresh_from_db()
        self.assertEqual(t.description, 'aggiornata')
        self.assertAlmostEqual(float(t.amount), -80.0)
        self.assertEqual(t.notes, 'nota')

    def test_import_update_ignores_wrong_owner(self):
        other_user = make_user(username='other', password='pass')
        other_cat = make_category(other_user, 'Food', 'EX')
        t = make_transaction(other_user, other_cat, -50, '2025-03-01', 'altrui')
        csv_file = build_csv([{
            'id': str(t.pk),
            'date': '2025-03-01', 'description': 'hackerata',
            'amount': '-80', 'category': 'Food', 'notes': '', 'is_recurring': 'False',
        }], include_id=True)
        self.client.post(reverse('core:transactions_import'), {'csv_file': csv_file})
        t.refresh_from_db()
        # La transazione dell'altro utente non deve essere modificata
        self.assertEqual(t.description, 'altrui')

    def test_import_auto_creates_unknown_category(self):
        csv_file = build_csv([{
            'date': '2025-06-01', 'description': 'nuova voce',
            'amount': '-30', 'category': 'BrandNew', 'notes': '', 'is_recurring': 'False',
        }])
        self.client.post(reverse('core:transactions_import'), {'csv_file': csv_file})
        # Category must have been created automatically
        self.assertTrue(Category.objects.filter(name='BrandNew', user=self.user).exists())
        # Transaction must have been imported, not skipped
        self.assertTrue(Transaction.objects.filter(user=self.user, description='nuova voce').exists())

    def test_import_auto_creates_income_category_for_positive_amount(self):
        csv_file = build_csv([{
            'date': '2025-06-02', 'description': 'stipendio',
            'amount': '2000', 'category': 'NewSalary', 'notes': '', 'is_recurring': 'False',
        }])
        self.client.post(reverse('core:transactions_import'), {'csv_file': csv_file})
        cat = Category.objects.filter(name='NewSalary', user=self.user).first()
        self.assertIsNotNone(cat)
        self.assertEqual(cat.type, Category.INCOME)

    def test_import_unknown_id_counts_as_error(self):
        csv_file = build_csv([{
            'id': '999999',
            'date': '2025-03-01', 'description': 'fantasma',
            'amount': '-50', 'category': 'Food', 'notes': '', 'is_recurring': 'False',
        }], include_id=True)
        response = self.client.post(
            reverse('core:transactions_import'), {'csv_file': csv_file}, follow=True
        )
        self.assertIn('saltate per errori', response.content.decode('utf-8'))


class BulkDeleteTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.login(username='csvuser', password='pass')
        self.cat = make_category(self.user, 'Food', 'EX')
        self.cat2 = make_category(self.user, 'Health', 'EX')
        make_transaction(self.user, self.cat, -100, '2025-01-10', 'spesa gennaio')
        make_transaction(self.user, self.cat, -200, '2025-02-10', 'spesa febbraio')
        make_transaction(self.user, self.cat2, -50, '2025-01-15', 'salute')

    def test_bulk_delete_all(self):
        self.client.post(reverse('core:transactions_bulk_delete'), {})
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 0)

    def test_bulk_delete_by_date_range(self):
        self.client.post(reverse('core:transactions_bulk_delete'), {
            'date_from': '2025-02-01', 'date_to': '2025-02-28',
        })
        remaining = Transaction.objects.filter(user=self.user)
        self.assertEqual(remaining.count(), 2)
        self.assertFalse(remaining.filter(description='spesa febbraio').exists())

    def test_bulk_delete_by_category(self):
        self.client.post(reverse('core:transactions_bulk_delete'), {
            'category': str(self.cat2.pk),
        })
        self.assertFalse(Transaction.objects.filter(user=self.user, description='salute').exists())
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 2)

    def test_bulk_delete_by_search(self):
        self.client.post(reverse('core:transactions_bulk_delete'), {
            'search': 'gennaio',
        })
        self.assertFalse(Transaction.objects.filter(user=self.user, description='spesa gennaio').exists())
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 2)

    def test_bulk_delete_does_not_affect_other_users(self):
        other = make_user(username='other', password='pass')
        other_cat = make_category(other, 'Food', 'EX')
        make_transaction(other, other_cat, -30, '2025-01-05', 'spesa altro utente')
        self.client.post(reverse('core:transactions_bulk_delete'), {})
        self.assertTrue(Transaction.objects.filter(user=other).exists())

    def test_bulk_delete_redirects_to_transaction_list(self):
        response = self.client.post(reverse('core:transactions_bulk_delete'), {})
        self.assertRedirects(response, reverse('core:transaction_list'))