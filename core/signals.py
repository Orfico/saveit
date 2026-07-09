from decimal import ROUND_HALF_UP, Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import Transaction
from core.utils.transaction_import import resolve_category_home_fallback


@receiver(post_save, sender=Transaction)
def propagate_family_transaction(sender, instance, created, **kwargs):
    """When a family-account transaction is saved, create or update halved copies
    for every linked individual member account."""

    # Derived copies must never re-propagate (prevents infinite recursion).
    if instance.source_transaction_id is not None:
        return

    # Only family accounts propagate.
    if not hasattr(instance.user, 'family_profile'):
        return

    memberships = instance.user.family_profile.linked_members.select_related('user').all()
    if not memberships.exists():
        return

    halved = (Decimal(str(instance.amount)) / 2).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    for fm in memberships:
        member_user = fm.user
        category = resolve_category_home_fallback(
            instance.category.name, float(halved), member_user
        )

        existing = Transaction.objects.filter(
            source_transaction=instance, user=member_user
        ).first()

        if existing:
            existing.date = instance.date
            existing.description = instance.description
            existing.amount = halved
            existing.category = category
            existing.notes = instance.notes
            existing.save()
        else:
            Transaction.objects.create(
                user=member_user,
                date=instance.date,
                description=instance.description,
                amount=halved,
                category=category,
                notes=instance.notes,
                is_recurring=False,
                paid_by=None,
                source_transaction=instance,
            )
