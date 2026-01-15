# core/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.db.models import Q
from .models import Transaction, Category


class CustomUserCreationForm(UserCreationForm):
    """Form di registrazione personalizzato"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'border border-gray-300 px-4 py-3 rounded-lg w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'tua@email.com'
        })
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'border border-gray-300 px-4 py-3 rounded-lg w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'nomeutente'
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
    """Form di login personalizzato"""
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
    # Campo per scegliere se è entrata o spesa
    transaction_type = forms.ChoiceField(
        choices=[
            ('expense', 'Spesa'),
            ('income', 'Entrata'),
        ],
        initial='expense',
        widget=forms.RadioSelect(attrs={
            'class': 'focus:ring-blue-500'
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
        label='Importo (sempre positivo)'
    )
    
    new_category_name = forms.CharField(
        max_length=100, 
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'border border-gray-300 px-3 py-2 rounded-lg w-full focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Nome nuova categoria',
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
        fields = ['date', 'description', 'category', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'border border-gray-300 px-4 py-2 rounded-lg w-full focus:ring-2 focus:ring-blue-500'
            }),
            'description': forms.TextInput(attrs={
                'class': 'border border-gray-300 px-4 py-2 rounded-lg w-full focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Es: Spesa al supermercato'
            }),
            'category': forms.Select(attrs={
                'class': 'border border-gray-300 px-4 py-2 rounded-lg w-full focus:ring-2 focus:ring-blue-500',
                'id': 'id_category'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'border border-gray-300 px-4 py-2 rounded-lg w-full focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Note aggiuntive (opzionale)'
            })
        }
    
    def __init__(self, *args, user=None, **kwargs):
        # Se stiamo modificando, estrai il tipo dalla transazione esistente
        instance = kwargs.get('instance')
        initial = kwargs.get('initial', {})
        
        if instance and instance.pk:
            # Modifica: imposta il tipo in base al segno dell'importo
            initial['transaction_type'] = 'income' if instance.amount > 0 else 'expense'
            initial['amount'] = abs(instance.amount)  # Mostra sempre positivo
            kwargs['initial'] = initial
        
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['category'].queryset = Category.objects.filter(
                Q(user=user) | Q(scope=Category.GLOBAL)
            ).order_by('type', 'name')
        
        self.fields['category'].required = False
    
    