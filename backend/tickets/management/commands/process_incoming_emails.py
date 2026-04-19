from django.core.management.base import BaseCommand
from tickets.email_utils import parse_incoming_email
import time

class Command(BaseCommand):
    help = 'Process incoming email replies and attach them to tickets'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run only once instead of watching continuously',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('📬 Starting email processor...'))
        
        if options['once']:
            self.process_emails()
        else:
            self.watch_continuously()
    
    def watch_continuously(self):
        """Run continuously, checking for emails every 10 seconds"""
        self.stdout.write(self.style.SUCCESS('Watching for incoming emails every 10 seconds. Press Ctrl+C to stop.'))
        
        try:
            while True:
                self.process_emails()
                time.sleep(10)
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('\n📬 Email processor stopped.'))
    
    def process_emails(self):
        """Simulate checking an email inbox and processing new messages"""
        
        # In real implementation, this would connect to an email server (IMAP/POP3)
        # For now, we'll simulate with a simple print
        
        self.stdout.write(self.style.WARNING('📨 Checking for new emails... (simulated)'))
        
        # Here's where you'd add actual email fetching logic
        # For now, we'll just print instructions for manual testing
        
        self.stdout.write(self.style.SQL_FIELD('\nTo test email threading manually:'))
        self.stdout.write(self.style.SQL_FIELD('1. Send an email to your test account'))
        self.stdout.write(self.style.SQL_FIELD('2. Subject must include: "Ticket #<id>"'))
        self.stdout.write(self.style.SQL_FIELD('3. Body will become conversation'))
        self.stdout.write(self.style.SQL_FIELD('4. From email must match customer email'))
        
        # Example manual test (commented out)
        """
        # This is how it would work with real email:
        subject = "Re: Ticket #3 - QuickCart Support"
        body = "Thanks for your help! When will my order arrive?"
        from_email = "test@example.com"
        
        ticket, conversation = parse_incoming_email(subject, body, from_email)
        
        if ticket and conversation:
            self.stdout.write(self.style.SUCCESS(f'✅ Processed reply for ticket #{ticket.id}'))
        else:
            self.stdout.write(self.style.ERROR('❌ Failed to process email'))
        """