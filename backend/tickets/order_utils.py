import re
import random
from datetime import datetime, timedelta

# Mock order database (simulates your actual order system)
MOCK_ORDERS = {
    "ORD-12345": {
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "status": "shipped",
        "order_date": "2026-02-25",
        "estimated_delivery": "2026-03-05",
        "tracking_number": "TRK-987654321",
        "carrier": "FedEx",
        "tracking_link": "https://www.fedex.com/tracking?tracking=987654321",
        "items": [
            {"name": "Wireless Headphones", "quantity": 1, "price": 79.99}
        ]
    },
    "ORD-67890": {
        "customer_name": "Jane Smith",
        "customer_email": "jane@example.com",
        "status": "processing",
        "order_date": "2026-02-28",
        "estimated_delivery": "2026-03-07",
        "tracking_number": None,
        "carrier": None,
        "tracking_link": None,
        "items": [
            {"name": "Laptop Stand", "quantity": 2, "price": 45.50}
        ]
    },
    "ORD-54321": {
        "customer_name": "Bob Wilson",
        "customer_email": "bob@example.com",
        "status": "delivered",
        "order_date": "2026-02-20",
        "delivered_date": "2026-02-28",
        "tracking_number": "TRK-123456789",
        "carrier": "UPS",
        "tracking_link": "https://www.ups.com/track?tracking=123456789",
        "items": [
            {"name": "Mechanical Keyboard", "quantity": 1, "price": 129.99}
        ]
    },
    "ORD-11111": {
        "customer_name": "Test User",
        "customer_email": "test@example.com",
        "status": "delayed",
        "order_date": "2026-02-15",
        "estimated_delivery": "2026-02-28",
        "delay_reason": "Weather conditions at sorting facility",
        "tracking_number": "TRK-555555555",
        "carrier": "USPS",
        "tracking_link": "https://tools.usps.com/go/TrackConfirmAction?tLabels=555555555",
        "items": [
            {"name": "Smart Watch", "quantity": 1, "price": 249.99}
        ]
    }
}

def extract_order_number(text):
    """
    Extract order number from text
    Looks for patterns like ORD-12345, order #12345, etc.
    """
    # Pattern 1: ORD-12345
    match = re.search(r'ORD[-_]?(\d{4,6})', text.upper())
    if match:
        return f"ORD-{match.group(1)}"
    
    # Pattern 2: order #12345
    match = re.search(r'order\s*[#:]?\s*(\d{4,8})', text.lower())
    if match:
        # Pad with zeros to make it look like ORD-12345
        order_num = match.group(1).zfill(5)
        return f"ORD-{order_num}"
    
    # Pattern 3: just numbers that look like order IDs (5-8 digits)
    match = re.search(r'\b(\d{5,8})\b', text)
    if match:
        return f"ORD-{match.group(1)}"
    
    return None

def get_order_status(order_number):
    """Get status for a given order number"""
    return MOCK_ORDERS.get(order_number)

def generate_status_message(order):
    """Generate a human-friendly status message"""
    
    status = order['status']
    
    if status == 'processing':
        return f"""
Your order #{order.get('order_number', 'N/A')} is being processed.

🔄 Status: Processing
📅 Ordered: {order['order_date']}
📦 Estimated delivery: {order['estimated_delivery']}

We'll notify you when it ships!
"""
    
    elif status == 'shipped':
        return f"""
Good news! Your order #{order.get('order_number', 'N/A')} has shipped!

🚚 Status: Shipped
📅 Shipped: {order.get('shipped_date', order['order_date'])}
📦 Estimated delivery: {order['estimated_delivery']}
📮 Tracking: {order['tracking_number']}
🚁 Carrier: {order['carrier']}
🔗 Track here: {order['tracking_link']}

You can also track using this number: {order['tracking_number']}
"""
    
    elif status == 'delivered':
        return f"""
Your order #{order.get('order_number', 'N/A')} has been delivered!

✅ Status: Delivered
📅 Delivered: {order.get('delivered_date', 'Recently')}

We hope you love your purchase! If you have any issues, please let us know.
"""
    
    elif status == 'delayed':
        return f"""
We're sorry, but your order #{order.get('order_number', 'N/A')} is delayed.

⚠️ Status: Delayed
📅 Ordered: {order['order_date']}
📦 Expected delivery: {order['estimated_delivery']}
💡 Reason: {order.get('delay_reason', 'Unknown delay')}

We're working to resolve this and will update you soon.
"""
    
    else:
        return f"""
Order #{order.get('order_number', 'N/A')} status: {status}

For more details, please contact support.
"""

def check_order_auto_response(ticket):
    """
    Check if ticket is about order status and auto-respond
    Returns: (responded, response_message)
    """
    # Combine title and description
    text = f"{ticket.title} {ticket.description}"
    
    # Look for order number
    order_number = extract_order_number(text)
    
    if not order_number:
        return False, None
    
    # Get order status
    order = get_order_status(order_number)
    
    if not order:
        return False, None
    
    # Add order number to the order dict
    order['order_number'] = order_number
    
    # Generate response
    response = generate_status_message(order)
    
    return True, response

# Order status history tracking
order_status_history = {}

def get_order_with_history(order_number):
    """Get order and track status changes"""
    order = MOCK_ORDERS.get(order_number)
    if not order:
        return None
    
    # Make a copy with order number
    order_with_number = order.copy()
    order_with_number['order_number'] = order_number
    
    # Track status for detecting changes
    if order_number not in order_status_history:
        order_status_history[order_number] = {
            'last_status': order['status'],
            'last_checked': datetime.now(),
            'notified_statuses': set([order['status']])  # Already notified on create
        }
    
    return order_with_number

def check_for_status_changes():
    """
    Check all orders for status changes
    Returns list of (order_number, old_status, new_status, order)
    """
    changes = []
    
    for order_number, order in MOCK_ORDERS.items():
        current_status = order['status']
        
        # Get history for this order
        history = order_status_history.get(order_number)
        
        # If no history, initialize it
        if not history:
            order_status_history[order_number] = {
                'last_status': current_status,
                'last_checked': datetime.now(),
                'notified_statuses': set([current_status])
            }
            continue
        
        # Check if status changed
        if current_status != history['last_status']:
            # Status changed!
            changes.append((
                order_number,
                history['last_status'],
                current_status,
                order
            ))
            
            # Update history
            history['last_status'] = current_status
            history['last_checked'] = datetime.now()
    
    return changes

def random_status_change():
    """
    FOR TESTING: Randomly change order status to simulate real updates
    """
    import random
    
    # Only change some orders randomly
    for order_number, order in MOCK_ORDERS.items():
        # 10% chance of status change
        if random.random() < 0.1:
            old_status = order['status']
            
            # Cycle through statuses
            if old_status == 'processing':
                order['status'] = 'shipped'
                order['shipped_date'] = datetime.now().strftime('%Y-%m-%d')
                order['tracking_number'] = f"TRK-{random.randint(100000000, 999999999)}"
                order['carrier'] = random.choice(['FedEx', 'UPS', 'USPS'])
                order['tracking_link'] = f"https://track.example.com/{order['tracking_number']}"
            elif old_status == 'shipped':
                order['status'] = 'delivered'
                order['delivered_date'] = datetime.now().strftime('%Y-%m-%d')
            elif old_status == 'delayed':
                order['status'] = 'shipped'
                order['shipped_date'] = datetime.now().strftime('%Y-%m-%d')
            
            print(f"🔄 TEST: Changed order {order_number} from {old_status} to {order['status']}")