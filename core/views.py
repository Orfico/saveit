# core/views.py

# Python standard library
import calendar
import json
import logging
import os
from django.conf import settings
from datetime import timedelta
from decimal import Decimal
from django.db import models
from collections import Counter

# Django core imports
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.views import View  # <-- ADDED THIS
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Sum, Q, Count
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView, DeleteView, DetailView,
    ListView, TemplateView, UpdateView, View,
)

# Django auth imports
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.views import LoginView
from django.contrib import messages

# Local imports
from .models import Transaction, Category, LoyaltyCard
from .forms import TransactionForm, CustomUserCreationForm, CustomAuthenticationForm
from .utils.barcode_generator import BarcodeGenerator

# Logger
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


class DashboardView(LoginRequiredMixin, ListView):
    template_name = 'core/dashboard.html'
    context_object_name = 'transactions'
    
    # Override queryset to filter by user and date range
    def get_queryset(self):
        queryset = Transaction.objects.filter(user=self.request.user).select_related('category')
        
        self.start_date = self.request.GET.get('start_date')
        self.end_date = self.request.GET.get('end_date')
        
        if not self.start_date:
            # First day of curent month
            today = timezone.now().date()
            self.start_date = today.replace(day=1)

        if not self.end_date:
            # Last day of current month
            today = timezone.now().date()
            last_day = calendar.monthrange(today.year, today.month)[1]
            self.end_date = today.replace(day=last_day)
        
        queryset = queryset.filter(date__range=[self.start_date, self.end_date])
        
        return queryset
    
    # Override context to add totals and pie chart data
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        
        # Dedicated totals for income, expenses, balance
        income = qs.filter(amount__gt=0).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        expenses = qs.filter(amount__lt=0).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        context['total_income'] = income
        context['total_expenses'] = abs(expenses)
        context['total_balance'] = income + expenses
        
        # Pie chart - Convert QuerySet to JSON
        pie_data_raw = qs.filter(
            amount__lt=0
        ).values(
            'category__name', 
            'category__color'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).filter(
            total__lt=0
        ).order_by('total')
        
        # Convert list of dictionaries to JSON-serializable format
        pie_list = []
        for item in pie_data_raw:
            pie_list.append({
                'category__name': item['category__name'],
                'category__color': item['category__color'] or '#3B82F6',
                'total': float(item['total']),  # Decimal → float
                'count': item['count']
            })

        context['pie_data_json'] = json.dumps(pie_list)  # JSON for JavaScript
        context['pie_data'] = pie_list  # List for template rendering
        context['start_date'] = self.start_date
        context['end_date'] = self.end_date
        
        return context


class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'core/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Transaction.objects.filter(user=self.request.user).select_related('category')
        
        # Search functionality
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                models.Q(description__icontains=search_query) |
                models.Q(notes__icontains=search_query) |
                models.Q(category__name__icontains=search_query)
            )
        
        # Category filter
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Date filters
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
        context['search_query'] = self.request.GET.get('search', '')  # Pass search to template
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
        """Save and handle new category creation"""
        print("🟢 FORM VALID - Start saving")  # ← DEBUG
        
        new_category_name = form.cleaned_data.get('new_category_name')
        
        if new_category_name:
            category, created = Category.objects.get_or_create(
                name=new_category_name,
                user=self.request.user,
                type=form.cleaned_data.get('category_type', Category.EXPENSE),
                defaults={
                    'scope': Category.PERSONAL,
                    'color': form.cleaned_data.get('category_color', '#3B82F6'),
                }
            )
            form.instance.category = category
   
        form.instance.user = self.request.user
        
        print(f"🟢 Transactions data:")  # ← DEBUG
        print(f"   User: {form.instance.user}")
        print(f"   Amount: {form.instance.amount}")
        print(f"   Category: {form.instance.category}")
        print(f"   Description: {form.instance.description}")
        print(f"   Is Recurring: {form.instance.is_recurring}")
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """Debug form errors"""
        print("🔴 FORM INVALID - Errors:")  # ← DEBUG
        print(form.errors)
        print(form.non_field_errors())
        return super().form_invalid(form)


class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    """View to update a transaction"""
    model = Transaction
    form_class = TransactionForm
    template_name = 'core/transaction_form.html'
    success_url = reverse_lazy('core:transaction_list')
    
    def get_queryset(self):
        # Only allow editing of user's own transactions
        return Transaction.objects.filter(user=self.request.user)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        new_category_name = form.cleaned_data.get('new_category_name')
        
        if new_category_name:
            category, created = Category.objects.get_or_create(
                name=new_category_name,
                user=self.request.user,
                type=form.cleaned_data.get('category_type', Category.EXPENSE),
                defaults={
                    'scope': Category.PERSONAL,
                    'color': form.cleaned_data.get('category_color', '#3B82F6'),
                }
            )
            form.instance.category = category
        
        return super().form_valid(form)


class TransactionDeleteView(LoginRequiredMixin, DeleteView):
    """View to delete a transaction"""
    model = Transaction
    template_name = 'core/transaction_confirm_delete.html'
    success_url = reverse_lazy('core:transaction_list')
    
    def get_queryset(self):
        # Only allow deleting of user's own transactions
        return Transaction.objects.filter(user=self.request.user)
    
class CustomLoginView(LoginView):
    """Login view"""
    form_class = CustomAuthenticationForm
    template_name = 'core/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('core:dashboard')
    
    def form_invalid(self, form):
        messages.error(self.request, 'Invalid Username or password.')
        return super().form_invalid(form)


class RegisterView(CreateView):
    """View for user registration"""
    form_class = CustomUserCreationForm
    template_name = 'core/register.html'
    success_url = reverse_lazy('core:dashboard')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # Auto-login after registration
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password1')
        user = authenticate(username=username, password=password)
        login(self.request, user)
        logger.info(f"✅ User registered successfully: {user.username}")
        messages.success(self.request, f'Welcome {username}! Your account has been created.')
        return response
    
    def form_invalid(self, form):
        logger.warning(f"❌ Registration failed with errors: {form.errors.as_json()}")
        messages.error(self.request, 'Registration failed. Please correct the errors below.')
        return super().form_invalid(form)   


def logout_view(request):
    """View to logout user"""
    logout(request)
    messages.success(request, 'Logout successful.')
    return redirect('core:login')

# ============= LOYALTY CARDS =============

class LoyaltyCardListView(LoginRequiredMixin, ListView):
    """List user's loyalty cards"""
    model = LoyaltyCard
    template_name = 'core/loyalty_cards_list.html'
    context_object_name = 'cards'
    
    def get_queryset(self):
        return LoyaltyCard.objects.filter(user=self.request.user)

class LoyaltyCardDetailView(LoginRequiredMixin, DetailView):
    """Display card barcode"""
    model = LoyaltyCard
    template_name = 'core/loyalty_card_detail.html'
    context_object_name = 'card'
    
    def get_queryset(self):
        return LoyaltyCard.objects.filter(user=self.request.user)
    

class LoyaltyCardDeleteView(LoginRequiredMixin, View):
    """Delete a loyalty card"""
    
    def post(self, request, pk):
        try:
            card = LoyaltyCard.objects.get(pk=pk, user=request.user)
            
            # Delete from S3 only if barcode image exists
            if card.barcode_image:
                try:
                    import boto3
                    s3_client = boto3.client(
                        's3',
                        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                        region_name=settings.AWS_S3_REGION_NAME,
                        config=boto3.session.Config(s3={'addressing_style': 'path'})
                    )
                    s3_client.delete_object(
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                        Key=card.barcode_image
                    )
                    logger.info(f"Deleted barcode from S3: {card.barcode_image}")
                except Exception as s3_error:
                    # Log error but continue with card deletion
                    logger.warning(f"Failed to delete barcode from S3: {str(s3_error)}")
            
            # Delete card from database
            card.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Card deleted successfully'
            })
            
        except LoyaltyCard.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Card not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error deleting card: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'Error deleting card'
            }, status=500)


@require_POST
def validate_barcode(request):
    """Validate barcode via AJAX"""
    try:
        data = json.loads(request.body)
        code = data.get('code', '')
        barcode_type = data.get('barcode_type', 'code128')
        
        is_valid = BarcodeGenerator.validate_code(code, barcode_type)
        
        return JsonResponse({
            'valid': is_valid,
            'message': 'Valid code' if is_valid else 'Invalid code for this format'
        })
        
    except Exception as e:
        return JsonResponse({
            'valid': False,
            'message': str(e)
        }, status=400)
    
class LoyaltyCardCreateView(LoginRequiredMixin, View):
    """Create a new loyalty card with barcode"""

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
                    'error': 'Store name and card number are required'
                }, status=400)

            # Generate barcode
            barcode_file, detected_type = BarcodeGenerator.generate_barcode(
                card_number, barcode_type
            )

            # Create LoyaltyCard instance
            card = LoyaltyCard(
                user=request.user,
                store_name=store_name,
                card_number=card_number,
                barcode_type=detected_type,
                notes=notes
            )

            # Check storage backend
            if os.environ.get('USE_S3', 'False') == 'True':
                # Upload to Supabase S3
                try:
                    import boto3
                    import re
                    from unicodedata import normalize
                    
                    s3_client = boto3.client(
                        's3',
                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                        region_name=settings.AWS_S3_REGION_NAME,
                        config=boto3.session.Config(s3={'addressing_style': 'path'})
                    )

                    # Sanitize filename - remove special characters
                    safe_store_name = normalize('NFKD', store_name).encode('ASCII', 'ignore').decode('ASCII')
                    safe_store_name = re.sub(r'[^\w\s-]', '', safe_store_name)
                    safe_store_name = safe_store_name.replace(' ', '_')
                    
                    filename = f"{safe_store_name}_{card_number}.png"
                    s3_path = f'barcodes/{filename}'

                    s3_client.put_object(
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                        Key=s3_path,
                        Body=barcode_file.read(),
                        ContentType='image/png'
                    )

                    card.barcode_image = s3_path
                    logger.info(f"Barcode uploaded to S3: {s3_path}")

                except Exception as e:
                    logger.error(f"Barcode upload failed: {e}")
                    return JsonResponse({
                        'success': False,
                        'error': 'Failed to upload barcode'
                    }, status=500)
            else:
                # Save to local media folder
                filename = f"{store_name.replace(' ', '_')}_{card_number}.png"
                local_path = os.path.join('barcodes', filename)
                full_path = os.path.join(settings.MEDIA_ROOT, local_path)
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                # Save the file
                with open(full_path, 'wb') as f:
                    f.write(barcode_file.read())
                
                # Normalize path for URL (forward slashes)
                card.barcode_image = local_path.replace('\\', '/')
                logger.info(f"Barcode saved locally: {local_path}")

            # Save card to database
            card.save()

            # Return success response
            return JsonResponse({
                'success': True,
                'card': {
                    'id': card.id,
                    'store_name': card.store_name,
                    'barcode_url': card.get_barcode_url()
                }
            })

        except Exception as e:
            logger.error(f"Error creating loyalty card: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
        
class CategoryDeleteView(LoginRequiredMixin, View):
    """Delete a category if it has no transactions"""
    
    def post(self, request, pk):
        try:
            category = Category.objects.get(pk=pk, user=request.user)
            
            # Check if category has transactions
            transaction_count = category.transactions.count()
            
            if transaction_count > 0:
                return JsonResponse({
                    'success': False,
                    'error': f'Cannot delete category with {transaction_count} transaction(s). Move or delete them first.'
                }, status=400)
            
            category_name = category.name
            category.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Category "{category_name}" deleted successfully'
            })
            
        except Category.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Category not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error deleting category: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'Error deleting category'
            }, status=500)
class CategoryListView(LoginRequiredMixin, ListView):
    """List and manage user categories"""
    model = Category
    template_name = 'core/categories_list.html'
    context_object_name = 'categories'
    
    def get_queryset(self):
        return Category.objects.filter(user=self.request.user).annotate(
            transaction_count=models.Count('transactions')
        ).order_by('type', 'name')
    
class RecurringTransactionsView(LoginRequiredMixin, ListView):
    """Manage recurring transaction templates"""
    model = Transaction
    template_name = 'core/recurring_transactions.html'
    context_object_name = 'recurring_transactions'
    
    def get_queryset(self):
        return Transaction.objects.filter(
            user=self.request.user,
            is_recurring=True
        ).select_related('category').order_by('-date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(user=self.request.user)
        return context
    
class RecurringTransactionDeleteView(LoginRequiredMixin, View):
    """Delete recurring master and optionally all copies"""
    
    def post(self, request, pk):
        try:
            data = json.loads(request.body)
            delete_copies = data.get('delete_copies', False)
            
            # Get master transaction
            master = Transaction.objects.get(pk=pk, user=request.user, is_recurring=True)
            
            deleted_count = 0
            
            # Delete copies if requested
            if delete_copies:
                # Find all copies: same user, category, description, amount
                copies = Transaction.objects.filter(
                    user=request.user,
                    category=master.category,
                    description=master.description,
                    amount=master.amount,
                    is_recurring=False,
                    date__gte=master.date  # Only future/current copies
                )
                deleted_count = copies.count()
                copies.delete()
            
            # Delete master
            master.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Recurring transaction deleted. {"" if not delete_copies else f"{deleted_count} copies also deleted."}'
            })
            
        except Transaction.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Recurring transaction not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error deleting recurring transaction: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

class RecurringTransactionUpdateView(LoginRequiredMixin, View):
    """Update recurring master and optionally all future copies"""
    
    def post(self, request, pk):
        try:
            data = json.loads(request.body)
            update_copies = data.get('update_copies', False)
            
            # Get master transaction
            master = Transaction.objects.get(pk=pk, user=request.user, is_recurring=True)
            
            # Store old values for finding copies
            old_category = master.category
            old_description = master.description
            old_amount = master.amount
            
            # Update master
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
            
            # Update future copies if requested
            if update_copies:
                today = timezone.now().date()
                copies = Transaction.objects.filter(
                    user=request.user,
                    category=old_category,
                    description=old_description,
                    amount=old_amount,
                    is_recurring=False,
                    date__gte=today  # Only future copies
                )
                
                updated_count = copies.update(
                    amount=master.amount,
                    category=master.category,
                    description=master.description,
                    notes=master.notes
                )
            
            return JsonResponse({
                'success': True,
                'message': f'Recurring transaction updated. {"" if not update_copies else f"{updated_count} future copies also updated."}'
            })
            
        except Transaction.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Recurring transaction not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error updating recurring transaction: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
        
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
 
        # ── Anno selezionato ────────────────────────────────────────────────
        available_years = sorted(
            set(
                list(user.transactions
                     .dates('date', 'year')
                     .values_list('date__year', flat=True)) +
                [current_year]
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
        income_by_month = [0.0] * 12
        expense_by_month = [0.0] * 12
 
        for item in qs.filter(amount__gt=0).values('date__month').annotate(t=Sum('amount')):
            income_by_month[item['date__month'] - 1] = float(item['t'])
 
        for item in qs.filter(amount__lt=0).values('date__month').annotate(t=Sum('amount')):
            expense_by_month[item['date__month'] - 1] = abs(float(item['t']))
 
        balance_by_month = [
            round(income_by_month[i] - expense_by_month[i], 2)
            for i in range(12)
        ]
 
        # ── Top 5 keyword nelle descrizioni delle uscite ────────────────────
        descriptions = qs.filter(amount__lt=0).values_list('description', flat=True)
        word_counter = Counter()
        for desc in descriptions:
            if desc:
                words = [w.lower().strip('.,;:!?()[]{}«»"\'') for w in desc.split()]
                word_counter.update(
                    w for w in words if len(w) > 2 and w not in ANALYTICS_STOPWORDS
                )
        top_keywords = word_counter.most_common(5)
 
        # ── Mese corrente vs media mesi precedenti (solo anno corrente) ─────
        month_vs_avg = None
        if selected_year == current_year and current_month >= 2:
            this_month_expense = expense_by_month[current_month - 1]
            past_expenses = [expense_by_month[i] for i in range(current_month - 1)]
            past_avg = sum(past_expenses) / len(past_expenses) if past_expenses else 0
            if past_avg > 0:
                diff_pct = ((this_month_expense - past_avg) / past_avg) * 100
                month_vs_avg = {
                    'this_month': this_month_expense,
                    'past_avg': past_avg,
                    'diff_pct': round(diff_pct, 1),
                    'is_over': diff_pct > 0,
                }
 
        # ── KPI di riepilogo ────────────────────────────────────────────────
        total_income = sum(income_by_month)
        total_expense = sum(expense_by_month)
        total_balance = total_income - total_expense
        savings_rate = (total_balance / total_income * 100) if total_income > 0 else 0
        months_with_expense = sum(1 for e in expense_by_month if e > 0)
        avg_monthly_expense = total_expense / months_with_expense if months_with_expense else 0
 
        ctx.update({
            'selected_year': selected_year,
            'available_years': available_years,
            'income_data': json.dumps(income_by_month),
            'expense_data': json.dumps(expense_by_month),
            'balance_data': json.dumps(balance_by_month),
            'top_keywords': top_keywords,
            'month_vs_avg': month_vs_avg,
            'total_income': total_income,
            'total_expense': total_expense,
            'total_balance': total_balance,
            'savings_rate': round(savings_rate, 1),
            'avg_monthly_expense': avg_monthly_expense,
        })
        return ctx
    