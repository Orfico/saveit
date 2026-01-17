from django.contrib import admin
from .models import Category, Transaction

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
    
    # Optional formatting (detail view)
    def get_amount_display(self, obj):
        return f"€{obj.amount:,.2f}"
    get_amount_display.short_description = 'Importo'
