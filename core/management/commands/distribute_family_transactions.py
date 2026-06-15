from datetime import date as date_type
from decimal import ROUND_HALF_UP, Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import FamilyProfile, Transaction
from core.utils.transaction_import import is_duplicate_transaction, resolve_category


class Command(BaseCommand):
    help = 'Copy today\'s family-account transactions to each linked individual member (halved amount).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            default=None,
            help='Target date in YYYY-MM-DD format (default: today).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without saving anything.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if options['date']:
            try:
                target_date = date_type.fromisoformat(options['date'])
            except ValueError:
                raise CommandError(f"Invalid date format: {options['date']}. Use YYYY-MM-DD.")
        else:
            target_date = timezone.now().date()

        if dry_run:
            self.stdout.write(self.style.WARNING(f'[DRY-RUN] Distributing transactions for {target_date}\n'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Distributing transactions for {target_date}\n'))

        family_profiles = FamilyProfile.objects.prefetch_related('linked_members__user').select_related('user')

        if not family_profiles.exists():
            self.stdout.write(self.style.WARNING('No family profiles found.\n'))
            return

        total_created = total_skipped = total_errors = 0

        for fp in family_profiles:
            members = list(fp.linked_members.select_related('user').all())
            if not members:
                self.stdout.write(f'  {fp}: no linked members — skipped.\n')
                continue

            transactions = Transaction.objects.filter(
                user=fp.user, date=target_date
            ).select_related('category')

            if not transactions.exists():
                self.stdout.write(f'  {fp}: no transactions on {target_date}.\n')
                continue

            self.stdout.write(f'  {fp}: {transactions.count()} transaction(s) → {len(members)} member(s)\n')

            for txn in transactions:
                halved = (Decimal(str(txn.amount)) / 2).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                for fm in members:
                    member_user = fm.user
                    try:
                        member_category = resolve_category(txn.category.name, float(halved), member_user)
                    except Exception as exc:
                        self.stdout.write(self.style.ERROR(
                            f'    ERROR resolving category "{txn.category.name}" for {member_user.username}: {exc}'
                        ))
                        total_errors += 1
                        continue

                    if is_duplicate_transaction(member_user, target_date, halved, member_category):
                        self.stdout.write(self.style.WARNING(
                            f'    SKIP duplicate: {member_user.username} / {txn.description or txn.category.name} / {halved}'
                        ))
                        total_skipped += 1
                        continue

                    if not dry_run:
                        Transaction.objects.create(
                            user=member_user,
                            date=target_date,
                            description=txn.description,
                            amount=halved,
                            category=member_category,
                            notes=txn.notes,
                            is_recurring=False,
                            paid_by=None,
                        )

                    self.stdout.write(self.style.SUCCESS(
                        f'    {"[DRY-RUN] Would create" if dry_run else "Created"}: '
                        f'{member_user.username} / {txn.description or txn.category.name} / {halved}'
                    ))
                    total_created += 1

        self.stdout.write('\n' + '=' * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY-RUN — nothing was saved.'))
        self.stdout.write(self.style.SUCCESS(f'Created:  {total_created}'))
        self.stdout.write(self.style.WARNING(f'Skipped:  {total_skipped}'))
        if total_errors:
            self.stdout.write(self.style.ERROR(f'Errors:   {total_errors}'))
        self.stdout.write('=' * 60 + '\n')
