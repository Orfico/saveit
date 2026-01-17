from django.core.management.base import BaseCommand
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from core.models import Transaction
from datetime import datetime

class Command(BaseCommand):
    help = 'Generate recurring transactions for the current month'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without creating transactions',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = timezone.now().date()
        current_month = today.month
        current_year = today.year
        
        self.stdout.write(self.style.SUCCESS(f'\n🔄 Generating recurring transactions for {current_month}/{current_year}\n'))
        
        # Find all active recurring transactions
        recurring_transactions = Transaction.objects.filter(is_recurring=True)
        
        if not recurring_transactions.exists():
            self.stdout.write(self.style.WARNING('⚠️  No recurring transactions found.\n'))
            return

        self.stdout.write(f'📋 Found {recurring_transactions.count()} recurring transactions\n')

        created_count = 0
        skipped_count = 0
        
        for original_transaction in recurring_transactions:
            # Calculate target date for the new transaction
            try:
                target_date = original_transaction.date.replace(
                    year=current_year,
                    month=current_month
                )
            except ValueError:
                # Handle end-of-month issues (e.g., Feb 30)
                target_date = (datetime(current_year, current_month, 1) + relativedelta(months=1, days=-1)).date()
            
            # Verify if this transaction already exists for the target month
            already_exists = Transaction.objects.filter(
                user=original_transaction.user,
                amount=original_transaction.amount,
                category=original_transaction.category,
                description=original_transaction.description,
                date=target_date
            ).exists()
            
            if already_exists:
                self.stdout.write(self.style.WARNING(
                    f'⏭️  Skipped: {original_transaction.description} - already exists for {target_date}'
                ))
                skipped_count += 1
                continue
            
            # Create the new transaction
            if not dry_run:
                new_transaction = Transaction.objects.create(
                    user=original_transaction.user,
                    amount=original_transaction.amount,
                    category=original_transaction.category,
                    description=original_transaction.description,
                    date=target_date,
                    is_recurring=False  # copy is not recurring, only the original is
                )
                
                self.stdout.write(self.style.SUCCESS(
                    f'✅ Created: {new_transaction.description} - €{new_transaction.amount} on {target_date}'
                ))
                created_count += 1
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'🔍 [DRY-RUN] Would create: {original_transaction.description} - €{original_transaction.amount} on {target_date}'
                ))
                created_count += 1
        
        # Summary
        self.stdout.write('\n' + '='*60)
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY-RUN MODE - No transactions created'))
        self.stdout.write(self.style.SUCCESS(f'✅ Created transactions: {created_count}'))
        self.stdout.write(self.style.WARNING(f'⏭️  Skipped transactions: {skipped_count}'))
        self.stdout.write('='*60 + '\n')