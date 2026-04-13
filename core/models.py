from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal


class Category(models.Model):
    INCOME = 'IN'
    EXPENSE = 'EX'
    TYPES = [
        (INCOME, 'Income'),
        (EXPENSE, 'Expense'),
    ]

    GLOBAL = 'GLOBAL'
    PERSONAL = 'PERSONAL'
    SCOPE_TYPES = [
        (GLOBAL, 'Global'),
        (PERSONAL, 'Personal'),
    ]

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=2, choices=TYPES, default=EXPENSE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    scope = models.CharField(max_length=10, choices=SCOPE_TYPES, default=PERSONAL)
    color = models.CharField(max_length=7, default='#3B82F6')

    @property
    def is_global(self):
        return self.scope == self.GLOBAL

    class Meta:
        unique_together = ('name', 'user', 'type')
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['type', 'name']
        indexes = [
            models.Index(fields=['user', 'scope']),
        ]

    def __str__(self):
        scope_indicator = '🌍' if self.is_global else '👤'
        return f'{scope_indicator} {self.get_type_display()}: {self.name}'


class FamilyProfile(models.Model):
    """Exists only for family accounts. Its presence signals the account type."""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='family_profile'
    )
    member_1 = models.CharField(max_length=100)
    member_2 = models.CharField(max_length=100)

    def __str__(self):
        return f'{self.member_1} & {self.member_2}'

    def member_name(self, key):
        """Return display name for 'member_1' or 'member_2'."""
        return self.member_1 if key == 'member_1' else self.member_2


class Transaction(models.Model):
    MEMBER_1 = 'member_1'
    MEMBER_2 = 'member_2'
    PAID_BY_CHOICES = [
        (MEMBER_1, 'Member 1'),
        (MEMBER_2, 'Member 2'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(default=timezone.now)
    description = models.TextField(max_length=500, blank=True)
    is_recurring = models.BooleanField(
        default=False,
        verbose_name='Monthly Recurring',
        help_text='If active, this transaction will repeat every month.',
    )
    notes = models.TextField(blank=True)
    paid_by = models.CharField(
        max_length=10,
        choices=PAID_BY_CHOICES,
        null=True,
        blank=True,
        help_text='Family accounts only: which member paid.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', '-date']),
            models.Index(fields=['category', '-date']),
        ]

    def __str__(self):
        return f'{self.category.name}: €{self.amount} ({self.date})'

    @property
    def is_income(self):
        return self.amount > 0

    @property
    def is_expense(self):
        return self.amount < 0

    @property
    def amount_abs(self):
        return abs(self.amount)

    @property
    def display_amount(self):
        if self.amount > 0:
            return f'+€{self.amount:.2f}'
        return f'-€{abs(self.amount):.2f}'


class LoyaltyCard(models.Model):
    BARCODE_TYPES = [
        ('code128', 'Code 128'),
        ('ean13', 'EAN-13'),
        ('ean8', 'EAN-8'),
        ('upca', 'UPC-A'),
        ('code39', 'Code 39'),
        ('itf', 'ITF'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loyalty_cards')
    store_name = models.CharField(max_length=100)
    card_number = models.CharField(max_length=50)
    barcode_type = models.CharField(
        max_length=20,
        choices=BARCODE_TYPES,
        default='code128',
        editable=False,
    )
    barcode_image = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['store_name']
        verbose_name = 'Loyalty Card'
        verbose_name_plural = 'Loyalty Cards'

    def __str__(self):
        return f'{self.store_name} - {self.card_number}'

    def get_barcode_url(self):
        import os
        if not self.barcode_image:
            return None
        if os.environ.get('USE_S3', 'False') == 'True':
            return f'https://wfoxqvvkutzbbphbbvvh.supabase.co/storage/v1/object/public/media/{self.barcode_image}'
        return f'/media/{self.barcode_image}'