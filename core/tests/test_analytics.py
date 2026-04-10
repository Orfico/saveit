# core/tests/test_analytics.py

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import Category, Transaction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username='testuser', password='pass'):
    return User.objects.create_user(username=username, password=password)


def make_category(user, name='Food', cat_type='EX'):
    return Category.objects.create(
        name=name,
        type=cat_type,
        user=user,
        scope='PERSONAL',
        color='#ff0000',
    )


def make_transaction(user, category, amount, date, description=''):
    return Transaction.objects.create(
        user=user,
        category=category,
        amount=amount,
        date=date,
        description=description,
    )


# ===========================================================================
# Accesso
# ===========================================================================

class AnalyticsAccessTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.url = reverse('core:analytics')

    def test_anonymous_user_is_redirected(self):
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)

    def test_authenticated_user_gets_200(self):
        self.client.login(username='testuser', password='pass')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/analytics.html')


# ===========================================================================
# KPI e dati di contesto
# ===========================================================================

class AnalyticsContextTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.login(username='testuser', password='pass')

        year = timezone.now().year
        cat_ex = make_category(self.user, 'Food', 'EX')
        cat_in = make_category(self.user, 'Salary', 'IN')

        make_transaction(self.user, cat_in,  1000, f'{year}-01-15', 'Stipendio gennaio')
        make_transaction(self.user, cat_ex,  -200, f'{year}-01-20', 'Spesa supermercato')
        make_transaction(self.user, cat_ex,   -50, f'{year}-02-10', 'Spesa supermercato')

    def test_total_income(self):
        response = self.client.get(reverse('core:analytics'))
        self.assertAlmostEqual(response.context['total_income'], 1000.0)

    def test_total_expense(self):
        response = self.client.get(reverse('core:analytics'))
        self.assertAlmostEqual(response.context['total_expense'], 250.0)

    def test_total_balance(self):
        response = self.client.get(reverse('core:analytics'))
        self.assertAlmostEqual(response.context['total_balance'], 750.0)

    def test_savings_rate(self):
        response = self.client.get(reverse('core:analytics'))
        self.assertEqual(response.context['savings_rate'], 75.0)

    def test_top_keywords_extracted(self):
        response = self.client.get(reverse('core:analytics'))
        keywords = [kw for kw, _ in response.context['top_keywords']]
        self.assertIn('supermercato', keywords)

    def test_user_isolation(self):
        """Un secondo utente non vede i dati del primo."""
        make_user('other', 'pass')
        self.client.login(username='other', password='pass')
        response = self.client.get(reverse('core:analytics'))
        self.assertEqual(response.context['total_income'], 0)
        self.assertEqual(response.context['total_expense'], 0)


# ===========================================================================
# Selezione anno
# ===========================================================================

class AnalyticsYearSelectorTest(TestCase):

    def setUp(self):
        self.user = make_user('yearuser', 'pass')
        self.client.login(username='yearuser', password='pass')
        cat = make_category(self.user)
        make_transaction(self.user, cat, -100, '2024-06-15', 'vecchia spesa')

    def test_available_years_includes_transaction_year(self):
        response = self.client.get(reverse('core:analytics'))
        self.assertIn(2024, response.context['available_years'])

    def test_available_years_includes_current_year(self):
        response = self.client.get(reverse('core:analytics'))
        self.assertIn(timezone.now().year, response.context['available_years'])

    def test_year_param_filters_data(self):
        response = self.client.get(reverse('core:analytics'), {'year': 2024})
        self.assertEqual(response.context['selected_year'], 2024)
        self.assertAlmostEqual(response.context['total_expense'], 100.0)

    def test_invalid_year_falls_back_to_current(self):
        response = self.client.get(reverse('core:analytics'), {'year': 'abc'})
        self.assertEqual(response.context['selected_year'], timezone.now().year)


# ===========================================================================
# Mese corrente vs media
# ===========================================================================

class AnalyticsMonthVsAvgTest(TestCase):

    def setUp(self):
        self.user = make_user('mvguser', 'pass')
        self.client.login(username='mvguser', password='pass')
        cat = make_category(self.user)
        year = timezone.now().year
        # Gennaio: 100 di uscite
        make_transaction(self.user, cat, -100, f'{year}-01-10', 'spesa gen')
        # Febbraio: 200 di uscite
        make_transaction(self.user, cat, -200, f'{year}-02-10', 'spesa feb')

    def test_month_vs_avg_absent_for_past_year(self):
        past_year = timezone.now().year - 1
        response = self.client.get(reverse('core:analytics'), {'year': past_year})
        self.assertIsNone(response.context['month_vs_avg'])

    def test_month_vs_avg_present_from_february_onwards(self):
        today = timezone.now()
        response = self.client.get(reverse('core:analytics'))
        if today.month >= 2:
            # Con dati sia a gennaio che al mese corrente, deve essere popolato
            ctx_val = response.context['month_vs_avg']
            if ctx_val is not None:
                self.assertIn('diff_pct', ctx_val)
                self.assertIn('is_over', ctx_val)
        else:
            self.assertIsNone(response.context['month_vs_avg'])