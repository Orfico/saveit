# core/views.py

# Python standard library
import calendar
import csv
import io
import json
import logging
import math
import os
from collections import Counter
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal

# Django core imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.db import models
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView, DeleteView, DetailView,
    ListView, TemplateView, UpdateView,
)

# Local imports
from .forms import CustomAuthenticationForm, CustomUserCreationForm, TransactionForm
from .models import Category, FamilyProfile, LoyaltyCard, Transaction
from .utils.barcode_generator import BarcodeGenerator

logger = logging.getLogger(__name__)

ANALYTICS_STOPWORDS = {
    'di', 'da', 'in', 'su', 'per', 'con', 'tra', 'fra',
    'del', 'della', 'dello', 'dei', 'degli', 'delle',
    'al', 'alla', 'allo', 'ai', 'agli', 'alle',
    'il', 'la', 'lo', 'i', 'gli', 'le',
    'un', 'una', 'uno', 'e', 'o', 'ma', 'se', 'che', 'non',
    'a', 'è', 'ho', 'ha', 'the', 'and', 'or', 'at', 'to',
    'of', 'for', 'on', 'by', 'with',
}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def is_family(user):
    return hasattr(user, 'family_profile')


# ===========================================================================
# AUTH
# ===========================================================================

class CustomLoginView(LoginView):
    form_class = CustomAuthenticationForm
    template_name = 'core/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('core:dashboard')

    def form_invalid(self, form):
        messages.error(self.request, 'Invalid Username or password.')
        return super().form_invalid(form)


class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'core/register.html'
    success_url = reverse_lazy('core:dashboard')

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.object

        # Family account setup
        if self.request.POST.get('is_family_account'):
            member_1 = self.request.POST.get('member_1', '').strip()
            member_2 = self.request.POST.get('member_2', '').strip()
            if member_1 and member_2:
                FamilyProfile.objects.create(
                    user=user, member_1=member_1, member_2=member_2,
                )
            else:
                messages.warning(
                    self.request,
                    'Account creato come standard: inserisci i nomi di entrambi i '
                    'membri per attivare la modalità famiglia.',
                )

        # Auto-login after registration
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password1')
        authenticated_user = authenticate(username=username, password=password)
        login(self.request, authenticated_user)
        logger.info(f"✅ User registered successfully: {user.username}")
        messages.success(self.request, f'Welcome {username}! Your account has been created.')
        return response

    def form_invalid(self, form):
        logger.warning(f"❌ Registration failed with errors: {form.errors.as_json()}")
        messages.error(self.request, 'Registration failed. Please correct the errors below.')
        return super().form_invalid(form)


def logout_view(request):
    logout(request)
    messages.success(request, 'Logout successful.')
    return redirect('core:login')


# ===========================================================================
# DASHBOARD
# ===========================================================================

class DashboardView(LoginRequiredMixin, ListView):
    template_name = 'core/dashboard.html'
    context_object_name = 'transactions'

    def get_queryset(self):
        queryset = Transaction.objects.filter(
            user=self.request.user
        ).select_related('category')

        self.start_date = self.request.GET.get('start_date')
        self.end_date = self.request.GET.get('end_date')

        if not self.start_date:
            today = timezone.now().date()
            self.start_date = today.replace(day=1)

        if not self.end_date:
            today = timezone.now().date()
            last_day = calendar.monthrange(today.year, today.month)[1]
            self.end_date = today.replace(day=last_day)

        return queryset.filter(date__range=[self.start_date, self.end_date])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        context['start_date'] = self.start_date
        context['end_date'] = self.end_date

        if is_family(self.request.user):
            context.update(self._family_context(self.request.user, qs))
        else:
            context.update(self._standard_context(qs))

        return context

    def _standard_context(self, qs):
        income = qs.filter(amount__gt=0).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        expenses = qs.filter(amount__lt=0).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        pie_data_raw = (
            qs.filter(amount__lt=0)
            .values('category__name', 'category__color')
            .annotate(total=Sum('amount'), count=Count('id'))
            .filter(total__lt=0)
            .order_by('total')
        )
        pie_list = [
            {
                'category__name': item['category__name'],
                'category__color': item['category__color'] or '#3B82F6',
                'total': float(item['total']),
                'count': item['count'],
            }
            for item in pie_data_raw
        ]

        return {
            'is_family': False,
            'total_income': income,
            'total_expenses': abs(expenses),
            'total_balance': income + expenses,
            'pie_data_json': json.dumps(pie_list),
            'pie_data': pie_list,
        }

    def _family_context(self, user, qs):
        fp = user.family_profile
        expenses = qs.filter(amount__lt=0)

        m1_total = abs(float(
            expenses.filter(paid_by=Transaction.MEMBER_1)
            .aggregate(t=Sum('amount'))['t'] or 0
        ))
        m2_total = abs(float(
            expenses.filter(paid_by=Transaction.MEMBER_2)
            .aggregate(t=Sum('amount'))['t'] or 0
        ))
        total = m1_total + m2_total
        fair_share = total / 2
        balance = round(m1_total - fair_share, 2)

        if balance > 0:
            debtor, creditor, debt = fp.member_2, fp.member_1, balance
        elif balance < 0:
            debtor, creditor, debt = fp.member_1, fp.member_2, abs(balance)
        else:
            debtor = creditor = None
            debt = 0

        pie_data_raw = (
            expenses.values('category__name', 'category__color')
            .annotate(total=Sum('amount'), count=Count('id'))
            .order_by('total')
        )
        pie_list = [
            {
                'category__name': item['category__name'],
                'category__color': item['category__color'] or '#3B82F6',
                'total': float(item['total']),
                'count': item['count'],
            }
            for item in pie_data_raw
        ]

        return {
            'is_family': True,
            'family_profile': fp,
            'total_expenses': total,
            'm1_total': m1_total,
            'm2_total': m2_total,
            'fair_share': fair_share,
            'debtor': debtor,
            'creditor': creditor,
            'debt': debt,
            'pie_data_json': json.dumps(pie_list),
            'pie_data': pie_list,
        }


# ===========================================================================
# TRANSACTIONS
# ===========================================================================

class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'core/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20

    def get_queryset(self):
        queryset = Transaction.objects.filter(
            user=self.request.user
        ).select_related('category')

        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(description__icontains=search_query) |
                Q(notes__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )

        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        return queryset.order_by('-date', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(user=self.request.user)
        context['search_query'] = self.request.GET.get('search', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['category_id'] = self.request.GET.get('category', '')
        context['search'] = self.request.GET.get('search', '')
        context['is_family'] = is_family(self.request.user)
        if context['is_family']:
            context['family_profile'] = self.request.user.family_profile
        return context


class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'core/transaction_form.html'
    success_url = reverse_lazy('core:transaction_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        new_category_name = form.cleaned_data.get('new_category_name')
        if new_category_name:
            category, _ = Category.objects.get_or_create(
                name=new_category_name,
                user=self.request.user,
                type=form.cleaned_data.get('category_type', Category.EXPENSE),
                defaults={
                    'scope': Category.PERSONAL,
                    'color': form.cleaned_data.get('category_color', '#3B82F6'),
                },
            )
            form.instance.category = category

        form.instance.user = self.request.user
        return super().form_valid(form)

    def form_invalid(self, form):
        logger.warning(f"Transaction form invalid: {form.errors}")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['is_family'] = is_family(self.request.user)
        if ctx['is_family']:
            ctx['family_profile'] = self.request.user.family_profile
        return ctx


class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'core/transaction_form.html'
    success_url = reverse_lazy('core:transaction_list')

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        new_category_name = form.cleaned_data.get('new_category_name')
        if new_category_name:
            category, _ = Category.objects.get_or_create(
                name=new_category_name,
                user=self.request.user,
                type=form.cleaned_data.get('category_type', Category.EXPENSE),
                defaults={
                    'scope': Category.PERSONAL,
                    'color': form.cleaned_data.get('category_color', '#3B82F6'),
                },
            )
            form.instance.category = category

        messages.success(self.request, 'Transazione aggiornata.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['is_family'] = is_family(self.request.user)
        if ctx['is_family']:
            ctx['family_profile'] = self.request.user.family_profile
        return ctx


class TransactionDeleteView(LoginRequiredMixin, DeleteView):
    model = Transaction
    template_name = 'core/transaction_confirm_delete.html'
    success_url = reverse_lazy('core:transaction_list')

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)


# ===========================================================================
# CATEGORIES
# ===========================================================================

class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'core/categories_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        qs = Category.objects.filter(
            Q(user=self.request.user) | Q(scope=Category.GLOBAL)
        ).annotate(
            transaction_count=models.Count('transactions')
        ).order_by('type', 'name')
        if is_family(self.request.user):
            qs = qs.filter(type=Category.EXPENSE)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['is_family'] = is_family(self.request.user)
        if ctx['is_family']:
            ctx['family_profile'] = self.request.user.family_profile
        return ctx


class CategoryCreateView(LoginRequiredMixin, View):
    def post(self, request):
        name = request.POST.get('name', '').strip()
        color = request.POST.get('color', '#3B82F6').strip()
        if is_family(request.user):
            cat_type = Category.EXPENSE
        else:
            cat_type = request.POST.get('type', Category.EXPENSE)
            if cat_type not in (Category.INCOME, Category.EXPENSE):
                cat_type = Category.EXPENSE

        if not name:
            messages.error(request, 'Il nome della categoria è obbligatorio.')
            return redirect('core:categories_list')

        _, created = Category.objects.get_or_create(
            name=name,
            user=request.user,
            type=cat_type,
            defaults={'scope': Category.PERSONAL, 'color': color},
        )
        if created:
            messages.success(request, f'Categoria "{name}" creata.')
        else:
            messages.warning(request, f'La categoria "{name}" esiste già.')

        return redirect('core:categories_list')


class CategoryDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            category = Category.objects.get(pk=pk, user=request.user)
            transaction_count = category.transactions.count()

            if transaction_count > 0:
                return JsonResponse({
                    'success': False,
                    'error': f'Cannot delete category with {transaction_count} transaction(s). Move or delete them first.',
                }, status=400)

            category_name = category.name
            category.delete()
            return JsonResponse({
                'success': True,
                'message': f'Category "{category_name}" deleted successfully',
            })

        except Category.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Category not found'}, status=404)
        except Exception as e:
            logger.error(f"Error deleting category: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'error': 'Error deleting category'}, status=500)


# ===========================================================================
# RECURRING TRANSACTIONS
# ===========================================================================

class RecurringTransactionsView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'core/recurring_transactions.html'
    context_object_name = 'recurring_transactions'

    def get_queryset(self):
        return Transaction.objects.filter(
            user=self.request.user,
            is_recurring=True,
        ).select_related('category').order_by('-date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(user=self.request.user)
        return context


class RecurringTransactionDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            data = json.loads(request.body)
            delete_copies = data.get('delete_copies', False)
            master = Transaction.objects.get(pk=pk, user=request.user, is_recurring=True)

            deleted_count = 0
            if delete_copies:
                copies = Transaction.objects.filter(
                    user=request.user,
                    category=master.category,
                    description=master.description,
                    amount=master.amount,
                    is_recurring=False,
                    date__gte=master.date,
                )
                deleted_count = copies.count()
                copies.delete()

            master.delete()
            return JsonResponse({
                'success': True,
                'message': f'Recurring transaction deleted. '
                           f'{"" if not delete_copies else f"{deleted_count} copies also deleted."}',
            })

        except Transaction.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Recurring transaction not found'}, status=404)
        except Exception as e:
            logger.error(f"Error deleting recurring transaction: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class RecurringTransactionUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            data = json.loads(request.body)
            update_copies = data.get('update_copies', False)
            master = Transaction.objects.get(pk=pk, user=request.user, is_recurring=True)

            old_category = master.category
            old_description = master.description
            old_amount = master.amount

            if 'amount' in data:
                master.amount = data['amount']
            if 'category_id' in data:
                master.category_id = data['category_id']
            if 'description' in data:
                master.description = data['description']
            if 'notes' in data:
                master.notes = data['notes']
            master.save()

            updated_count = 0
            if update_copies:
                today = timezone.now().date()
                copies = Transaction.objects.filter(
                    user=request.user,
                    category=old_category,
                    description=old_description,
                    amount=old_amount,
                    is_recurring=False,
                    date__gte=today,
                )
                updated_count = copies.update(
                    amount=master.amount,
                    category=master.category,
                    description=master.description,
                    notes=master.notes,
                )

            return JsonResponse({
                'success': True,
                'message': f'Recurring transaction updated. '
                           f'{"" if not update_copies else f"{updated_count} future copies also updated."}',
            })

        except Transaction.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Recurring transaction not found'}, status=404)
        except Exception as e:
            logger.error(f"Error updating recurring transaction: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ===========================================================================
# CSV EXPORT / IMPORT
# ===========================================================================

class ExportTransactionsView(LoginRequiredMixin, View):
    def get(self, request):
        qs = Transaction.objects.select_related('category').filter(user=request.user)
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        category_id = request.GET.get('category')
        search = request.GET.get('search', '').strip()

        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if search:
            qs = qs.filter(
                Q(description__icontains=search) |
                Q(notes__icontains=search) |
                Q(category__name__icontains=search)
            )
        qs = qs.order_by('-date', '-created_at')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
        writer = csv.writer(response)
        writer.writerow(['date', 'description', 'amount', 'category', 'notes', 'is_recurring', 'paid_by'])
        for t in qs:
            writer.writerow([
                t.date, t.description, t.amount, t.category.name,
                t.notes, t.is_recurring, t.paid_by or '',
            ])
        return response


class ImportTransactionsView(LoginRequiredMixin, View):
    def post(self, request):
        csv_file = request.FILES.get('csv_file')
        if not csv_file or not csv_file.name.endswith('.csv'):
            messages.error(request, 'Carica un file CSV valido.')
            return redirect('core:transaction_list')

        imported = skipped = errors = 0
        try:
            decoded = csv_file.read().decode('utf-8')
            try:
                dialect = csv.Sniffer().sniff(decoded[:2048], delimiters=',;\t')
            except csv.Error:
                dialect = csv.excel
            reader = csv.DictReader(io.StringIO(decoded), dialect=dialect)

            # Date normalization: accept YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, DD-MM-YYYY
            from datetime import datetime as dt
            DATE_FORMATS = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']

            def parse_date(raw):
                raw = raw.strip()
                for fmt in DATE_FORMATS:
                    try:
                        return dt.strptime(raw, fmt).date().isoformat()
                    except ValueError:
                        continue
                raise ValueError(f'Unrecognised date format: {raw}')

            # Build paid_by name→key map for family accounts
            paid_by_map = {}
            if is_family(request.user):
                fp = request.user.family_profile
                paid_by_map = {
                    fp.member_1.strip().lower(): Transaction.MEMBER_1,
                    fp.member_2.strip().lower(): Transaction.MEMBER_2,
                    Transaction.MEMBER_1: Transaction.MEMBER_1,
                    Transaction.MEMBER_2: Transaction.MEMBER_2,
                }

            for row_num, row in enumerate(reader, start=2):
                try:
                    amount_val = float(row['amount'].strip())
                    # Family accounts: all transactions are expenses
                    if paid_by_map:
                        amount_val = -abs(amount_val)
                    primary_type = Category.EXPENSE if amount_val < 0 else Category.INCOME
                    fallback_type = Category.INCOME if amount_val < 0 else Category.EXPENSE

                    category = Category.objects.filter(
                        Q(user=request.user) | Q(scope=Category.GLOBAL),
                        name=row['category'].strip(),
                        type=primary_type,
                    ).order_by('scope').first()

                    if not category:
                        category = Category.objects.filter(
                            Q(user=request.user) | Q(scope=Category.GLOBAL),
                            name=row['category'].strip(),
                            type=fallback_type,
                        ).order_by('scope').first()

                    if not category:
                        logger.warning(
                            f'CSV import row {row_num}: categoria "{row["category"]}" '
                            f'non trovata — riga saltata.'
                        )
                        errors += 1
                        continue

                    parsed_date = parse_date(row['date'])

                    if Transaction.objects.filter(
                        user=request.user,
                        date=parsed_date,
                        amount=amount_val,
                        category=category,
                    ).exists():
                        logger.info(
                            f'CSV import row {row_num}: duplicato ignorato — '
                            f'{row["date"]} {amount_val} {category.name}'
                        )
                        skipped += 1
                        continue

                    # Resolve paid_by: accepts real names or member_1/member_2 keys
                    raw_paid_by = row.get('paid_by', '').strip()
                    if paid_by_map:
                        paid_by = paid_by_map.get(raw_paid_by.lower()) or None
                        if raw_paid_by and not paid_by:
                            logger.warning(
                                f'CSV import row {row_num}: paid_by "{raw_paid_by}" '
                                f'non riconosciuto — impostato a None.'
                            )
                    else:
                        paid_by = raw_paid_by or None

                    Transaction.objects.create(
                        user=request.user,
                        date=parsed_date,
                        description=row.get('description', '').strip(),
                        amount=amount_val,
                        category=category,
                        notes=row.get('notes', '').strip(),
                        is_recurring=row.get('is_recurring', 'False').strip() == 'True',
                        paid_by=paid_by,
                    )
                    imported += 1
                except Exception as e:
                    logger.error(f'CSV import row {row_num}: errore — {e}')
                    errors += 1

        except Exception as e:
            logger.error(f'CSV import: errore lettura file — {e}')
            messages.error(request, 'Errore durante la lettura del file.')
            return redirect('core:transaction_list')

        parts = [f'{imported} transazioni importate']
        if skipped:
            parts.append(f'{skipped} duplicate ignorate')
        if errors:
            parts.append(f'{errors} righe saltate per errori')
        messages.success(request, ' · '.join(parts) + '.')
        return redirect('core:transaction_list')


# ===========================================================================
# LOYALTY CARDS
# ===========================================================================

class LoyaltyCardListView(LoginRequiredMixin, ListView):
    model = LoyaltyCard
    template_name = 'core/loyalty_cards_list.html'
    context_object_name = 'cards'

    def get_queryset(self):
        return LoyaltyCard.objects.filter(user=self.request.user)


class LoyaltyCardDetailView(LoginRequiredMixin, DetailView):
    model = LoyaltyCard
    template_name = 'core/loyalty_card_detail.html'
    context_object_name = 'card'

    def get_queryset(self):
        return LoyaltyCard.objects.filter(user=self.request.user)


class LoyaltyCardCreateView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            store_name = data.get('store_name', '').strip()
            card_number = data.get('card_number', '').strip()
            barcode_type = data.get('barcode_type', 'code128')
            notes = data.get('notes', '').strip()

            if not store_name or not card_number:
                return JsonResponse({
                    'success': False,
                    'error': 'Store name and card number are required',
                }, status=400)

            barcode_file, detected_type = BarcodeGenerator.generate_barcode(
                card_number, barcode_type
            )

            card = LoyaltyCard(
                user=request.user,
                store_name=store_name,
                card_number=card_number,
                barcode_type=detected_type,
                notes=notes,
            )

            if os.environ.get('USE_S3', 'False') == 'True':
                try:
                    import re
                    from unicodedata import normalize
                    import boto3

                    s3_client = boto3.client(
                        's3',
                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                        region_name=settings.AWS_S3_REGION_NAME,
                        config=boto3.session.Config(s3={'addressing_style': 'path'}),
                    )
                    safe_store_name = normalize('NFKD', store_name).encode('ASCII', 'ignore').decode('ASCII')
                    safe_store_name = re.sub(r'[^\w\s-]', '', safe_store_name).replace(' ', '_')
                    filename = f"{safe_store_name}_{card_number}.png"
                    s3_path = f'barcodes/{filename}'
                    s3_client.put_object(
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                        Key=s3_path,
                        Body=barcode_file.read(),
                        ContentType='image/png',
                    )
                    card.barcode_image = s3_path
                    logger.info(f"Barcode uploaded to S3: {s3_path}")
                except Exception as e:
                    logger.error(f"Barcode upload failed: {e}")
                    return JsonResponse({'success': False, 'error': 'Failed to upload barcode'}, status=500)
            else:
                filename = f"{store_name.replace(' ', '_')}_{card_number}.png"
                local_path = os.path.join('barcodes', filename)
                full_path = os.path.join(settings.MEDIA_ROOT, local_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'wb') as f:
                    f.write(barcode_file.read())
                card.barcode_image = local_path.replace('\\', '/')
                logger.info(f"Barcode saved locally: {local_path}")

            card.save()
            return JsonResponse({
                'success': True,
                'card': {
                    'id': card.id,
                    'store_name': card.store_name,
                    'barcode_url': card.get_barcode_url(),
                },
            })

        except Exception as e:
            logger.error(f"Error creating loyalty card: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class LoyaltyCardDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            card = LoyaltyCard.objects.get(pk=pk, user=request.user)

            if card.barcode_image:
                try:
                    import boto3
                    s3_client = boto3.client(
                        's3',
                        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                        region_name=settings.AWS_S3_REGION_NAME,
                        config=boto3.session.Config(s3={'addressing_style': 'path'}),
                    )
                    s3_client.delete_object(
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                        Key=card.barcode_image,
                    )
                    logger.info(f"Deleted barcode from S3: {card.barcode_image}")
                except Exception as s3_error:
                    logger.warning(f"Failed to delete barcode from S3: {str(s3_error)}")

            card.delete()
            return JsonResponse({'success': True, 'message': 'Card deleted successfully'})

        except LoyaltyCard.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Card not found'}, status=404)
        except Exception as e:
            logger.error(f"Error deleting card: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'error': 'Error deleting card'}, status=500)


@require_POST
def validate_barcode(request):
    try:
        data = json.loads(request.body)
        code = data.get('code', '')
        barcode_type = data.get('barcode_type', 'code128')
        is_valid = BarcodeGenerator.validate_code(code, barcode_type)
        return JsonResponse({
            'valid': is_valid,
            'message': 'Valid code' if is_valid else 'Invalid code for this format',
        })
    except Exception as e:
        return JsonResponse({'valid': False, 'message': str(e)}, status=400)


# ===========================================================================
# ANALYTICS
# ===========================================================================

class AnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = 'core/analytics.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.now()
        current_year = today.year
        current_month = today.month
        family = is_family(user)

        # ── Anno selezionato ────────────────────────────────────────────────
        available_years = sorted(
            set(
                list(user.transactions.dates('date', 'year')
                     .values_list('date__year', flat=True)) + [current_year]
            ),
            reverse=True,
        )
        try:
            selected_year = int(self.request.GET.get('year', current_year))
        except (ValueError, TypeError):
            selected_year = current_year
        if selected_year not in available_years:
            selected_year = current_year

        qs = user.transactions.filter(date__year=selected_year)

        # ── Dati mensili ────────────────────────────────────────────────────
        expense_by_month = [0.0] * 12
        income_by_month = [0.0] * 12

        for item in qs.filter(amount__lt=0).values('date__month').annotate(t=Sum('amount')):
            expense_by_month[item['date__month'] - 1] = abs(float(item['t']))

        if not family:
            for item in qs.filter(amount__gt=0).values('date__month').annotate(t=Sum('amount')):
                income_by_month[item['date__month'] - 1] = float(item['t'])

        balance_by_month = [
            round(income_by_month[i] - expense_by_month[i], 2)
            for i in range(12)
        ]

        # ── Top 5 merchant per frequenza (descrizione esatta) ───────────────
        from collections import Counter
        merchant_counter = Counter()
        for desc in qs.filter(amount__lt=0).values_list('description', flat=True):
            if desc and desc.strip():
                merchant_counter[desc.strip()] += 1
        top_keywords = merchant_counter.most_common(5)  # (description, count)

        # ── Spese per giorno della settimana ─────────────────────────────────
        WEEKDAYS_LABELS = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']
        weekday_totals = [0.0] * 7
        for t_date, t_amount in qs.filter(amount__lt=0).values_list('date', 'amount'):
            weekday_totals[t_date.weekday()] += abs(float(t_amount))

        # ── Mese tipo EWM vs mese corrente ──────────────────────────────────
        month_vs_avg = None
        if selected_year == current_year and current_month >= 2:
            import calendar as cal
            from datetime import date as date_cls
            today_date = today.date()
            decay = math.log(2) / 180

            # Aggregate by month first, then weight each monthly total by recency
            monthly_totals = (
                user.transactions
                .filter(amount__lt=0)
                .exclude(date__year=current_year, date__month=current_month)
                .values('date__year', 'date__month')
                .annotate(total=Sum('amount'))
            )

            weighted_sum = weight_total = 0.0
            for item in monthly_totals:
                y, m = item['date__year'], item['date__month']
                last_day = cal.monthrange(y, m)[1]
                ref_date = date_cls(y, m, last_day)
                days_ago = (today_date - ref_date).days
                if days_ago > 0:
                    w = math.exp(-decay * days_ago)
                    weighted_sum += abs(float(item['total'])) * w
                    weight_total += w

            if weight_total > 0:
                typical_month = weighted_sum / weight_total  # weighted avg of monthly totals
                this_month_expense = expense_by_month[current_month - 1]
                diff_pct = ((this_month_expense - typical_month) / typical_month) * 100
                month_vs_avg = {
                    'this_month': this_month_expense,
                    'past_avg': round(typical_month, 2),
                    'diff_pct': round(diff_pct, 1),
                    'is_over': diff_pct > 0,
                }

        # ── KPI ─────────────────────────────────────────────────────────────
        total_income = sum(income_by_month)
        total_expense = sum(expense_by_month)
        total_balance = total_income - total_expense
        savings_rate = (total_balance / total_income * 100) if total_income > 0 else 0
        months_with_expense = sum(1 for e in expense_by_month if e > 0)
        avg_monthly_expense = total_expense / months_with_expense if months_with_expense else 0

        # ── Family: ripartizione per membro ─────────────────────────────────
        member_breakdown = None
        if family:
            fp = user.family_profile
            m1_by_month = [0.0] * 12
            m2_by_month = [0.0] * 12
            for item in (qs.filter(amount__lt=0, paid_by=Transaction.MEMBER_1)
                         .values('date__month').annotate(t=Sum('amount'))):
                m1_by_month[item['date__month'] - 1] = abs(float(item['t']))
            for item in (qs.filter(amount__lt=0, paid_by=Transaction.MEMBER_2)
                         .values('date__month').annotate(t=Sum('amount'))):
                m2_by_month[item['date__month'] - 1] = abs(float(item['t']))
            member_breakdown = {
                'member_1_name': fp.member_1,
                'member_2_name': fp.member_2,
                'member_1_data': json.dumps(m1_by_month),
                'member_2_data': json.dumps(m2_by_month),
                'member_1_total': sum(m1_by_month),
                'member_2_total': sum(m2_by_month),
            }

        # ── Entrate per categoria (solo account standard) ───────────────────
        income_by_category = []
        if not family:
            cat_qs = (
                qs.filter(amount__gt=0)
                .values('category__name', 'category__color')
                .annotate(total=Sum('amount'))
                .order_by('-total')
            )
            income_by_category = [
                {
                    'name': c['category__name'],
                    'total': float(c['total']),
                    'color': c['category__color'] or '#3B82F6',
                }
                for c in cat_qs
            ]

        ctx.update({
            'is_family': family,
            'family_profile': user.family_profile if family else None,
            'selected_year': selected_year,
            'available_years': available_years,
            'expense_data': json.dumps(expense_by_month),
            'income_data': json.dumps(income_by_month),
            'balance_data': json.dumps(balance_by_month),
            'top_keywords': top_keywords,
            'weekday_data': json.dumps(weekday_totals),
            'weekday_labels': json.dumps(['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']),
            'month_vs_avg': month_vs_avg,
            'total_income': total_income,
            'total_expense': total_expense,
            'total_balance': total_balance,
            'savings_rate': round(savings_rate, 1),
            'avg_monthly_expense': avg_monthly_expense,
            'member_breakdown': member_breakdown,
            'income_by_category': json.dumps(income_by_category),
        })
        return ctx