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
        unique_together = ('name', 'user', 'type')  # Prevents duplicate names per user and type
        verbose_name = "Category"
        verbose_name_plural = "Categories" 
        ordering = ['type', 'name']  # Order by type then name
        indexes = [
            models.Index(fields=['user', 'scope']),  # Improves query performance
        ]
    
    def __str__(self):
        scope_indicator = "🌍" if self.is_global else "👤"
        return f"{scope_indicator} {self.get_type_display()}: {self.name}"


class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2) 
    date = models.DateField(default=timezone.now)
    description = models.TextField(max_length=500, blank=True)
    is_recurring = models.BooleanField(
        default=False, 
        verbose_name="Montlhy Recurring",
        help_text="If active, this transaction will repeat every month."
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  #  Tracking
    updated_at = models.DateTimeField(auto_now=True)      #  Tracking
    
    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', '-date']),  # Improves query performance
            models.Index(fields=['category', '-date']),
        ]
    
    def __str__(self):
        return f"{self.category.name}: €{self.amount} ({self.date})"
    
    @property
    def is_income(self):
        """Helper for template"""
        return self.amount > 0
    
    @property
    def is_expense(self):
        """Helper for template"""
        return self.amount < 0
    
    @property
    def amount_abs(self):
        """Returns the absolute value of the amount."""
        return abs(self.amount)
    
    @property
    def display_amount(self):
        """Returns the amount formatted with sign for display."""
        if self.amount > 0:
            return f"+€{self.amount:.2f}"
        else:
            return f"-€{abs(self.amount):.2f}"

class LoyaltyCard(models.Model):
    """Model for loyalty cards and membership cards"""
    
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
        editable=False  # ✅ Not editable by user, set automatically
    )
    barcode_image = models.ImageField(upload_to='barcodes/', blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Loyalty Card'
        verbose_name_plural = 'Loyalty Cards'
    
    def __str__(self):
        return f"{self.store_name} - {self.card_number}"