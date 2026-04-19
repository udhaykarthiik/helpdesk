from django.core.management.base import BaseCommand
from tickets.ticket_updater import update_tickets_for_status_changes
from tickets.order_utils import random_status_change
import time

class Command(BaseCommand):
    help = 'Check for order status changes and update tickets'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run only once',
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Add random status changes for testing',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔄 Starting order status monitor...'))
        
        if options['test']:
            self.stdout.write(self.style.WARNING('Test mode: Will randomly change order statuses'))
        
        if options['once']:
            self.run_once(options['test'])
        else:
            self.run_continuous(options['test'])
    
    def run_once(self, test_mode):
        if test_mode:
            random_status_change()
        
        updates = update_tickets_for_status_changes()
        
        if updates:
            self.stdout.write(self.style.SUCCESS(f'✅ Updated {len(updates)} tickets'))
            for update in updates:
                self.stdout.write(f"  - Ticket #{update['ticket_id']}: {update['order_number']} {update['old_status']} → {update['new_status']}")
        else:
            self.stdout.write(self.style.WARNING('No status changes detected'))
    
    def run_continuous(self, test_mode):
        self.stdout.write(self.style.SUCCESS('Watching for order changes every 30 seconds. Press Ctrl+C to stop.'))
        
        try:
            while True:
                if test_mode:
                    random_status_change()
                
                updates = update_tickets_for_status_changes()
                
                if updates:
                    self.stdout.write(self.style.SUCCESS(f'✅ Updated {len(updates)} tickets'))
                else:
                    self.stdout.write('.', ending='')
                
                time.sleep(30)
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('\n🔄 Order status monitor stopped.'))