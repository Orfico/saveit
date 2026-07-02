# core/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'core'

urlpatterns = [
    # Autenticazione
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Password Reset
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='core/password_reset.html',
             email_template_name='registration/password_reset_email.html',
             subject_template_name='registration/password_reset_subject.txt',
             success_url='/password-reset/done/'
         ), 
         name='password_reset'),
    
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='core/password_reset_done.html'
         ), 
         name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='core/password_reset_confirm.html',
             success_url='/password-reset-complete/'
         ), 
         name='password_reset_confirm'),
    
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='core/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    
    # Dashboard e Transazioni
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('transactions/', views.TransactionListView.as_view(), name='transaction_list'),
    path('transactions/new/', views.TransactionCreateView.as_view(), name='transaction_create'),
    path('transactions/export/', views.ExportTransactionsView.as_view(), name='transactions_export'),
    path('transactions/import/', views.ImportTransactionsView.as_view(), name='transactions_import'),
    path('transactions/bulk-delete/', views.BulkDeleteTransactionsView.as_view(), name='transactions_bulk_delete'),
    path('transactions/sync-family/', views.SyncFamilyTransactionsView.as_view(), name='transactions_sync_family'),
    path('transactions/<int:pk>/edit/', views.TransactionUpdateView.as_view(), name='transaction_update'),
    path('transactions/<int:pk>/delete/', views.TransactionDeleteView.as_view(), name='transaction_delete'),

    # Categories
    path('categories/', views.CategoryListView.as_view(), name='categories_list'),
    path('categories/create/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_edit'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),

    # Recurring Transactions
    path('recurring-transactions/', views.RecurringTransactionsView.as_view(), name='recurring_transactions'),
    path('recurring-transactions/<int:pk>/update/', views.RecurringTransactionUpdateView.as_view(), name='recurring_transaction_update'),
    path('recurring-transactions/<int:pk>/delete/', views.RecurringTransactionDeleteView.as_view(), name='recurring_transaction_delete'),

    # Loyalty Cards
    path('loyalty-cards/', views.LoyaltyCardListView.as_view(), name='loyalty_cards_list'),
    path('loyalty-cards/create/', views.LoyaltyCardCreateView.as_view(), name='loyalty_card_create'),
    path('loyalty-cards/<int:pk>/', views.LoyaltyCardDetailView.as_view(), name='loyalty_card_detail'),
    path('loyalty-cards/<int:pk>/delete/', views.LoyaltyCardDeleteView.as_view(), name='loyalty_card_delete'),
    path('loyalty-cards/validate/', views.validate_barcode, name='validate_barcode'),

    # ── Analytics ────────────────────────────────────────────────────────────
    path('analytics/', views.AnalyticsView.as_view(), name='analytics'),

    # ── Settings & Account Switching ─────────────────────────────────────────
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('settings/members/add/', views.AddFamilyMemberView.as_view(), name='settings_add_member'),
    path('settings/members/<int:pk>/remove/', views.RemoveFamilyMemberView.as_view(), name='settings_remove_member'),
    path('settings/switch/<int:user_pk>/', views.SwitchAccountView.as_view(), name='account_switch'),
    path('settings/switch-back/', views.SwitchBackView.as_view(), name='account_switch_back'),
]