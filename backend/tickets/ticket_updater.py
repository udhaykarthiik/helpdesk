from .models import Ticket, Conversation, Customer
from .order_utils import check_for_status_changes, get_order_with_history, generate_status_message
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

def find_ticket_for_order(order_number, customer_email):
    """
    Find the most recent ticket for this order and customer
    """
    try:
        customer = Customer.objects.get(email=customer_email)
        
        # Look for tickets containing this order number
        tickets = Ticket.objects.filter(
            customer=customer,
            title__icontains='order',
            created_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).order_by('-created_at')
        
        # Try to find one with this specific order number
        for ticket in tickets:
            if order_number in ticket.title or order_number in ticket.description:
                return ticket
        
        # If no exact match, return most recent order-related ticket
        return tickets.first()
        
    except Customer.DoesNotExist:
        return None

def update_tickets_for_status_changes():
    """
    Main function to check for order status changes and update tickets
    """
    # Check for status changes
    changes = check_for_status_changes()
    
    if not changes:
        logger.info("No order status changes detected")
        return []
    
    updated_tickets = []
    
    for order_number, old_status, new_status, order in changes:
        logger.info(f"Order {order_number} changed: {old_status} → {new_status}")
        
        # Find ticket for this order
        ticket = find_ticket_for_order(order_number, order['customer_email'])
        
        if not ticket:
            logger.info(f"No ticket found for order {order_number}")
            continue
        
        # Add order number to order dict for message generation
        order['order_number'] = order_number
        
        # Generate status message
        status_message = generate_status_message(order)
        
        # Add prefix indicating status change
        full_message = f"🔔 **ORDER UPDATE**: Your order status changed from {old_status} to {new_status}!\n\n{status_message}"
        
        # Create conversation
        conversation = Conversation.objects.create(
            ticket=ticket,
            sender_type='agent',
            message=full_message,
            is_internal_note=False
        )
        
        updated_tickets.append({
            'ticket_id': ticket.id,
            'order_number': order_number,
            'old_status': old_status,
            'new_status': new_status,
            'conversation_id': conversation.id
        })
        
        logger.info(f"✅ Updated ticket #{ticket.id} with order status change")
    
    return updated_tickets