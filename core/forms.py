# core/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.db.models import Q
from .models import Transaction, Category


class CustomUserCreationForm(UserCreationForm):
    """Customized registration form"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'border border-gray-300 px-4 py-3 rounded-lg w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'your@email.com'
        })
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'border border-gray-300 px-4 py-3 rounded-lg w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'username'
        })
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'border border-gray-300 px-4 py-3 rounded-lg w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': '••••••••'
        })
    )
    password2 = forms.CharField(
        label='Conferma Password',
        widget=forms.PasswordInput(attrs={
            'class': 'border border-gray-300 px-4 py-3 rounded-lg w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': '••••••••'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """Customized login form"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'border border-gray-300 px-4 py-3 rounded-lg w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Username',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'border border-gray-300 px-4 py-3 rounded-lg w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Password'
        })
    )


class TransactionForm(forms.ModelForm):
    """Form for creating/editing transactions"""
    
    # Field to indicate type (expense/income)
    type = forms.ChoiceField(
        choices=[
            ('expense', 'Expense'),
            ('income', 'Income'),
        ],
        initial='expense',
        widget=forms.RadioSelect(attrs={
            'class': 'w-4 h-4 text-blue-600 focus:ring-blue-500'
        }),
        label='Tipo'
    )
    
    # Importo sempre positivo
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class': 'border border-gray-300 px-4 py-2 rounded-lg w-full focus:ring-2 focus:ring-blue-500',
            'step': '0.01',
            'placeholder': '0.00'
        }),
        label='Amount (always positive)'
    )
    
    # Campi per creare nuova categoria al volo
    new_category_name = forms.CharField(
        max_length=100, 
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'border border-gray-300 px-3 py-2 rounded-lg w-full focus:ring-2 focus:ring-blue-500',
            'placeholder': 'New Category Name',
            'id': 'new_category_input'
        })
    )
    
    category_type = forms.ChoiceField(
        choices=Category.TYPES,
        required=False,
        initial=Category.EXPENSE,
        widget=forms.Select(attrs={
            'class': 'border border-gray-300 px-3 py-2 rounded-lg w-full focus:ring-2 focus:ring-blue-500',
            'id': 'category_type'
        })
    )
    
    category_color = forms.CharField(
        max_length=7,
        required=False,
        initial='#3B82F6',
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'border border-gray-300 rounded-lg w-full h-10 cursor-pointer',
            'id': 'category_color'
        })
    )
    
    class Meta:
        model = Transaction
        fields = ['date', 'description', 'category', 'notes', 'is_recurring']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'border border-gray-300 px-4 py-2 rounded-lg w-full focus:ring-2 focus:ring-blue-500'
            }),
            'description': forms.TextInput(attrs={
                'class': 'border border-gray-300 px-4 py-2 rounded-lg w-full focus:ring-2 focus:ring-blue-500',
                'placeholder': 'E.g.: Grociery shopping'
            }),
            'category': forms.Select(attrs={
                'class': 'border border-gray-300 px-4 py-2 rounded-lg w-full focus:ring-2 focus:ring-blue-500',
                'id': 'id_category'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'border border-gray-300 px-4 py-2 rounded-lg w-full focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Additional notes (optional)'
            }),
            'is_recurring': forms.CheckboxInput(attrs={
                'class': 'sr-only peer'
            }),
        }
    
    def __init__(self, *args, user=None, **kwargs):
        """Initialize form with user-specific category filtering"""
        instance = kwargs.get('instance')
        initial = kwargs.get('initial', {})
        
        if instance and instance.pk:
            # Modifica: imposta il tipo in base al segno dell'importo
            initial['type'] = 'income' if instance.amount > 0 else 'expense'
            initial['amount'] = abs(instance.amount)  # Mostra sempre positivo
            kwargs['initial'] = initial
        
        super().__init__(*args, **kwargs)
        
        # Filter categories by user and global
        if user:
            self.fields['category'].queryset = Category.objects.filter(
                Q(user=user) | Q(scope=Category.GLOBAL)
            ).order_by('type', 'name')
        
        self.fields['category'].required = False
    
    def clean(self):
        """Validate the form"""
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        new_category_name = cleaned_data.get('new_category_name', '').strip()
        
        # Validazione categoria
        if not category and not new_category_name:
            raise forms.ValidationError(
                'You must select an existing category or enter a new category name.'
            )
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save transaction with correct amount sign"""
        instance = super().save(commit=False)
        
        # Convert amount based on type
        amount = self.cleaned_data.get('amount')
        type = self.cleaned_data.get('type')
        
        if type == 'expense':
            instance.amount = -abs(amount)  # Expense = negative
        else:
            instance.amount = abs(amount)   # Income = positive

        if commit:
            instance.save()
        
        return instance