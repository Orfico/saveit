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
    
    # ✅ Password Reset
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
    path('transactions/<int:pk>/edit/', views.TransactionUpdateView.as_view(), name='transaction_update'),
    path('transactions/<int:pk>/delete/', views.TransactionDeleteView.as_view(), name='transaction_delete'),
]