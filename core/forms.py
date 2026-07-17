# core/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from .models import Transaction, Category, FamilyProfile


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
        label=_('Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'border border-gray-300 px-4 py-3 rounded-lg w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': '••••••••'
        })
    )
    password2 = forms.CharField(
        label=_('Confirm Password'),
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

    # Field to indicate type (expense/income) — hidden for family accounts
    type = forms.ChoiceField(
        choices=[
            ('expense', 'Expense'),
            ('income', 'Income'),
        ],
        initial='expense',
        widget=forms.RadioSelect(attrs={
            'class': 'w-4 h-4 text-blue-600 focus:ring-blue-500'
        }),
        label=_('Type'),
    )

    # Amount field always positive
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class': 'border border-gray-300 px-4 py-2 rounded-lg w-full focus:ring-2 focus:ring-blue-500',
            'step': '0.01',
            'placeholder': '0.00'
        }),
        label=_('Amount (always positive)'),
    )

    # Fields for new category creation
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
        fields = ['date', 'description', 'category', 'notes', 'is_recurring',
                  'recurrence_interval', 'recurrence_days', 'paid_by']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'border border-gray-300 px-4 py-2 rounded-lg w-full focus:ring-2 focus:ring-blue-500'
            }),
            'description': forms.TextInput(attrs={
                'class': 'border border-gray-300 px-4 py-2 rounded-lg w-full focus:ring-2 focus:ring-blue-500',
                'placeholder': 'E.g.: Grocery shopping'
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
            'recurrence_interval': forms.Select(attrs={
                'class': 'border border-gray-300 px-3 py-2 rounded-lg w-full focus:ring-2 focus:ring-blue-500 text-sm',
                'id': 'id_recurrence_interval',
            }),
            'recurrence_days': forms.NumberInput(attrs={
                'class': 'border border-gray-300 px-3 py-2 rounded-lg w-full focus:ring-2 focus:ring-blue-500 text-sm',
                'min': '1',
                'placeholder': '30',
                'id': 'id_recurrence_days',
            }),
            'paid_by': forms.Select(attrs={
                'class': 'border border-gray-300 px-4 py-2 rounded-lg w-full focus:ring-2 focus:ring-blue-500',
            }),
        }

    def clean_recurrence_interval(self):
        return self.cleaned_data.get('recurrence_interval') or 'monthly'

    def __init__(self, *args, user=None, **kwargs):
        instance = kwargs.get('instance')
        initial = kwargs.get('initial', {})

        if instance and instance.pk:
            initial['type'] = 'income' if instance.amount > 0 else 'expense'
            initial['amount'] = abs(instance.amount)
            kwargs['initial'] = initial

        super().__init__(*args, **kwargs)
        self.fields['recurrence_interval'].required = False

        # Filter categories by user and global
        if user:
            self.fields['category'].queryset = Category.objects.filter(
                Q(user=user) | Q(scope=Category.GLOBAL)
            ).order_by('type', 'name')

        self.fields['category'].required = False

        # Family account configuration
        self._is_family = False
        if user:
            try:
                fp = user.family_profile
                self._is_family = True
                # type is always expense for family — render as hidden
                self.fields['type'].widget = forms.HiddenInput()
                self.fields['type'].initial = 'expense'
                self.fields['is_recurring'].widget = forms.HiddenInput()
                self.fields['is_recurring'].initial = False
                self.fields['recurrence_interval'].widget = forms.HiddenInput()
                self.fields['recurrence_days'].widget = forms.HiddenInput()
                # paid_by is required with actual member names
                self.fields['paid_by'].required = True
                self.fields['paid_by'].choices = [
                    ('', '---------'),
                    (Transaction.MEMBER_1, fp.member_1),
                    (Transaction.MEMBER_2, fp.member_2),
                ]
                # Only expense categories
                self.fields['category'].queryset = self.fields['category'].queryset.filter(
                    type=Category.EXPENSE
                )
            except FamilyProfile.DoesNotExist:
                # Standard account — paid_by not used
                self.fields['paid_by'].widget = forms.HiddenInput()
                self.fields['paid_by'].required = False

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        new_category_name = cleaned_data.get('new_category_name', '').strip()

        if not category and not new_category_name:
            raise forms.ValidationError(
                _('You must select an existing category or enter a new category name.')
            )

        # Ensure type defaults to expense if missing (family hidden field fallback)
        if not cleaned_data.get('type'):
            cleaned_data['type'] = 'expense'

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        amount = self.cleaned_data.get('amount')
        t = self.cleaned_data.get('type', 'expense')

        if t == 'expense':
            instance.amount = -abs(amount)
        else:
            instance.amount = abs(amount)

        if commit:
            instance.save()

        return instance