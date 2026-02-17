from django.contrib import admin
from .models import Category, Transaction, LoyaltyCard

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'type_display', 'scope', 'user_display']
    list_filter = ['type', 'scope']
    search_fields = ['name']
    
    def type_display(self, obj):  
        return getattr(obj, 'get_type_display', lambda: '')()
    type_display.short_description = 'Tipo'
    
    def user_display(self, obj):
        return "🌍 Global" if obj.user is None else str(obj.user)
    user_display.short_description = 'Utente'

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['date', 'amount', 'category', 'description']
    list_filter = ['date', 'category', 'user']
    search_fields = ['description']
    date_hierarchy = 'date'
    list_per_page = 25

@admin.register(LoyaltyCard)
class LoyaltyCardAdmin(admin.ModelAdmin):
    list_display = ['store_name', 'user', 'card_number', 'barcode_type', 'created_at']
    list_filter = ['barcode_type', 'created_at', 'user']
    search_fields = ['store_name', 'card_number', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Card Information', {
            'fields': ('user', 'store_name', 'card_number', 'barcode_type')
        }),
        ('Barcode', {
            'fields': ('barcode_image',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Optional formatting (detail view)
    def get_amount_display(self, obj):
        return f"€{obj.amount:,.2f}"
    get_amount_display.short_description = 'Importo'
