from django.core.management.base import BaseCommand
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from core.models import Transaction
from datetime import datetime

class Command(BaseCommand):
    help = 'Genera le transazioni ricorrenti mensili per il mese corrente'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra cosa verrebbe fatto senza creare transazioni',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = timezone.now().date()
        current_month = today.month
        current_year = today.year
        
        self.stdout.write(self.style.SUCCESS(f'\n🔄 Generazione transazioni ricorrenti per {current_month}/{current_year}\n'))
        
        # Trova tutte le transazioni ricorrenti attive
        recurring_transactions = Transaction.objects.filter(is_recurring=True)
        
        if not recurring_transactions.exists():
            self.stdout.write(self.style.WARNING('⚠️  Nessuna transazione ricorrente trovata.\n'))
            return
        
        self.stdout.write(f'📋 Trovate {recurring_transactions.count()} transazioni ricorrenti\n')
        
        created_count = 0
        skipped_count = 0
        
        for original_transaction in recurring_transactions:
            # Calcola la data target (stesso giorno del mese corrente)
            try:
                target_date = original_transaction.date.replace(
                    year=current_year,
                    month=current_month
                )
            except ValueError:
                # Gestisce casi tipo 31 febbraio -> usa l'ultimo giorno del mese
                target_date = (datetime(current_year, current_month, 1) + relativedelta(months=1, days=-1)).date()
            
            # Verifica se esiste già una transazione per questo mese
            already_exists = Transaction.objects.filter(
                user=original_transaction.user,
                amount=original_transaction.amount,
                category=original_transaction.category,
                description=original_transaction.description,
                date=target_date
            ).exists()
            
            if already_exists:
                self.stdout.write(self.style.WARNING(
                    f'⏭️  Saltata: {original_transaction.description} - già esiste per {target_date}'
                ))
                skipped_count += 1
                continue
            
            # Crea la nuova transazione
            if not dry_run:
                new_transaction = Transaction.objects.create(
                    user=original_transaction.user,
                    type=original_transaction.type,
                    amount=original_transaction.amount,
                    category=original_transaction.category,
                    description=original_transaction.description,
                    date=target_date,
                    is_recurring=False  # La copia NON è ricorrente, solo l'originale
                )
                
                self.stdout.write(self.style.SUCCESS(
                    f'✅ Creata: {new_transaction.description} - €{new_transaction.amount} il {target_date}'
                ))
                created_count += 1
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'🔍 [DRY-RUN] Creerebbe: {original_transaction.description} - €{original_transaction.amount} il {target_date}'
                ))
                created_count += 1
        
        # Summary
        self.stdout.write('\n' + '='*60)
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 MODALITÀ DRY-RUN - Nessuna transazione creata'))
        self.stdout.write(self.style.SUCCESS(f'✅ Transazioni create: {created_count}'))
        self.stdout.write(self.style.WARNING(f'⏭️  Transazioni saltate: {skipped_count}'))
        self.stdout.write('='*60 + '\n')