from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Transaction


def next_occurrence(current_date, interval, recurrence_days=None):
    """Return the next occurrence date after current_date for the given interval."""
    if interval == Transaction.WEEKLY:
        return current_date + timedelta(days=7)
    elif interval == Transaction.ANNUALLY:
        return current_date + relativedelta(years=1)
    elif interval == Transaction.CUSTOM:
        return current_date + timedelta(days=recurrence_days or 30)
    else:  # monthly (default)
        return current_date + relativedelta(months=1)


class Command(BaseCommand):
    help = 'Generate all due recurring transactions up to today'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without creating transactions',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = timezone.now().date()

        self.stdout.write(self.style.SUCCESS(f'\n🔄 Generating recurring transactions up to {today}\n'))

        recurring_transactions = Transaction.objects.filter(
            is_recurring=True
        ).select_related('category', 'user')

        if not recurring_transactions.exists():
            self.stdout.write(self.style.WARNING('⚠️  No recurring transactions found.\n'))
            return

        self.stdout.write(f'📋 Found {recurring_transactions.count()} recurring transactions\n')

        created_count = 0
        skipped_count = 0

        for master in recurring_transactions:
            # Start from the most recent copy so we never regenerate old ones
            last_copy = Transaction.objects.filter(
                user=master.user,
                amount=master.amount,
                category=master.category,
                description=master.description,
                is_recurring=False,
            ).order_by('-date').first()

            current_date = last_copy.date if last_copy else master.date

            while True:
                target_date = next_occurrence(
                    current_date,
                    master.recurrence_interval,
                    master.recurrence_days,
                )

                if target_date > today:
                    break

                already_exists = Transaction.objects.filter(
                    user=master.user,
                    amount=master.amount,
                    category=master.category,
                    description=master.description,
                    date=target_date,
                ).exists()

                if already_exists:
                    self.stdout.write(self.style.WARNING(
                        f'⏭️  Skipped: {master.description} - already exists for {target_date}'
                    ))
                    skipped_count += 1
                elif not dry_run:
                    Transaction.objects.create(
                        user=master.user,
                        amount=master.amount,
                        category=master.category,
                        description=master.description,
                        notes=master.notes,
                        date=target_date,
                        is_recurring=False,
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f'✅ Created: {master.description} - €{master.amount} on {target_date}'
                    ))
                    created_count += 1
                else:
                    self.stdout.write(self.style.SUCCESS(
                        f'🔍 [DRY-RUN] Would create: {master.description} - €{master.amount} on {target_date}'
                    ))
                    created_count += 1

                current_date = target_date

        self.stdout.write('\n' + '=' * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY-RUN MODE - No transactions created'))
        self.stdout.write(self.style.SUCCESS(f'✅ Created transactions: {created_count}'))
        self.stdout.write(self.style.WARNING(f'⏭️  Skipped transactions: {skipped_count}'))
        self.stdout.write('=' * 60 + '\n')
