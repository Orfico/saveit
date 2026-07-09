"""Shared helpers for importing transactions (CSV import view, signals, management commands)."""
from django.db.models import Q

from core.models import Category, Transaction


def resolve_category(cat_name, amount_val, user):
    """Return a Category for *user* matching *cat_name* and the sign of *amount_val*.

    Search order:
      1. User-owned or global category with the primary type (EXPENSE if amount < 0, else INCOME).
      2. Same but with the fallback type.
      3. Auto-create a PERSONAL category with the primary type if nothing is found.
    """
    primary_type = Category.EXPENSE if amount_val < 0 else Category.INCOME
    fallback_type = Category.INCOME if primary_type == Category.EXPENSE else Category.EXPENSE

    base_qs = Category.objects.filter(Q(user=user) | Q(scope=Category.GLOBAL))

    category = base_qs.filter(name=cat_name, type=primary_type).order_by('scope').first()
    if not category:
        category = base_qs.filter(name=cat_name, type=fallback_type).order_by('scope').first()
    if not category:
        category, _ = Category.objects.get_or_create(
            name=cat_name,
            user=user,
            type=primary_type,
            defaults={'scope': Category.PERSONAL, 'color': '#3B82F6'},
        )
    return category


def is_duplicate_transaction(user, date, amount, category):
    """Return True if a transaction with these exact attributes already exists for *user*."""
    return Transaction.objects.filter(
        user=user, date=date, amount=amount, category=category,
    ).exists()


def resolve_category_home_fallback(cat_name, amount_val, user):
    """Like resolve_category but falls back to a 'home' category instead of auto-creating one."""
    primary_type = Category.EXPENSE if amount_val < 0 else Category.INCOME
    fallback_type = Category.INCOME if primary_type == Category.EXPENSE else Category.EXPENSE
    base_qs = Category.objects.filter(Q(user=user) | Q(scope=Category.GLOBAL))
    category = base_qs.filter(name=cat_name, type=primary_type).order_by('scope').first()
    if not category:
        category = base_qs.filter(name=cat_name, type=fallback_type).order_by('scope').first()
    if not category:
        category = base_qs.filter(name__iexact='home').order_by('scope').first()
        if not category:
            category, _ = Category.objects.get_or_create(
                name='home',
                user=user,
                type=Category.EXPENSE,
                defaults={'scope': Category.PERSONAL, 'color': '#3B82F6'},
            )
    return category
