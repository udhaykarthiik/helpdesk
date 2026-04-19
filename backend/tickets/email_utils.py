import re
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Ticket, Conversation, Customer

def send_ticket_confirmation(ticket):
    """Send confirmation email when ticket is created"""
    
    subject = f"Ticket #{ticket.id} Received - QuickCart Support"
    
    message = f"""
Dear {ticket.customer.name},

Thank you for contacting QuickCart Support. Your ticket has been created successfully.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TICKET DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ticket ID: #{ticket.id}
Subject: {ticket.title}
Status: {ticket.status}
Created: {ticket.created_at.strftime('%B %d, %Y at %I:%M %p')}

Your Message:
{ticket.description}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IMPORTANT: To reply to this ticket, simply REPLY to this email. Your reply will be automatically added to the ticket.

We will respond within 24 hours.

Thanks,
QuickCart Support Team
    """
    
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [ticket.customer.email]
    
    send_mail(
        subject,
        message,
        from_email,
        recipient_list,
        fail_silently=False,
    )
    
    print(f"📧 Confirmation email sent for ticket #{ticket.id} to {ticket.customer.email}")

def send_reply_notification(ticket, conversation):
    """Send email notification when agent replies to ticket"""
    
    subject = f"Re: Ticket #{ticket.id} - QuickCart Support"
    
    message = f"""
Dear {ticket.customer.name},

An agent has responded to your ticket.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TICKET #{ticket.id}: {ticket.title}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AGENT RESPONSE:
{conversation.message}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

To continue this conversation, simply REPLY to this email.

Thanks,
QuickCart Support Team
    """
    
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [ticket.customer.email]
    
    send_mail(
        subject,
        message,
        from_email,
        recipient_list,
        fail_silently=False,
    )
    
    print(f"📧 Reply notification sent for ticket #{ticket.id} to {ticket.customer.email}")

def parse_incoming_email(email_subject, email_body, from_email):
    """
    Process incoming email replies
    Returns: (ticket, conversation) if successful, (None, None) if not
    """
    
    # Step 1: Extract ticket ID from subject
    # Subject format: "Re: Ticket #123 - QuickCart Support"
    match = re.search(r'Ticket #(\d+)', email_subject)
    
    if not match:
        print(f"❌ Could not find ticket ID in subject: {email_subject}")
        return None, None
    
    ticket_id = match.group(1)
    
    # Step 2: Find the ticket
    try:
        ticket = Ticket.objects.get(id=ticket_id)
    except Ticket.DoesNotExist:
        print(f"❌ Ticket #{ticket_id} not found")
        return None, None
    
    # Step 3: Verify sender is the customer
    try:
        customer = Customer.objects.get(email=from_email)
        if customer.id != ticket.customer.id:
            print(f"❌ Email from {from_email} does not match ticket customer {ticket.customer.email}")
            return None, None
    except Customer.DoesNotExist:
        print(f"❌ Customer with email {from_email} not found")
        return None, None
    
    # Step 4: Create conversation from email
    conversation = Conversation.objects.create(
        ticket=ticket,
        sender_type='customer',
        message=email_body.strip(),
        is_internal_note=False
    )
    
    print(f"📨 Incoming email processed: Ticket #{ticket.id} - New conversation #{conversation.id}")
    
    return ticket, conversation