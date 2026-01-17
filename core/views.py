# core/views.py
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Sum, Q, Count
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import Transaction, Category
from .forms import TransactionForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.views import LoginView
from django.views.generic import CreateView
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomAuthenticationForm


class DashboardView(LoginRequiredMixin, ListView):
    template_name = 'core/dashboard.html'
    context_object_name = 'transactions'
    
    # Override queryset to filter by user and date range
    def get_queryset(self):
        queryset = Transaction.objects.filter(user=self.request.user).select_related('category')
        
        self.start_date = self.request.GET.get('start_date')
        self.end_date = self.request.GET.get('end_date')
        
        if not self.start_date:
            self.start_date = (timezone.now().date() - timedelta(days=30))
        if not self.end_date:
            self.end_date = timezone.now().date()
        
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
        qs = Transaction.objects.select_related('category').filter(
            user=self.request.user
        )
        
        # Filters with validations
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        category_id = self.request.GET.get('category')
        search = self.request.GET.get('search', '').strip()
        
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if search:
            qs = qs.filter(
                Q(description__icontains=search) |
                Q(notes__icontains=search) |  # Search in notes as well
                Q(category__name__icontains=search)
            )
        
        return qs.order_by('-date', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # User + global categories for filter dropdown
        context['categories'] = Category.objects.filter(
            Q(user=self.request.user) | Q(scope=Category.GLOBAL)
        ).order_by('type', 'name')
        
        # Keep filter values in context
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['category_id'] = self.request.GET.get('category', '')
        context['search'] = self.request.GET.get('search', '')
        
        # ✅ Rapid summary
        qs = self.get_queryset()
        context['filtered_count'] = qs.count()
        context['filtered_total'] = qs.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
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
        messages.success(self.request, f'Welcome {username}! Your account has been created.')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Registration failed. Please correct the errors below.')
        return super().form_invalid(form)


def logout_view(request):
    """View to logout user"""
    logout(request)
    messages.success(request, 'Logout successful.')
    return redirect('core:login')