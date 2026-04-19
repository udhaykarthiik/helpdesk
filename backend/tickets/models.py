from django.db import models
from django.contrib.auth.models import User
import re
import json
import os

class Organization(models.Model):
    """QuickCart is one organization - this allows for multi-tenancy"""
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Customer(models.Model):
    """People who buy from QuickCart"""
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_vip = models.BooleanField(default=False)
    vip_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=50000.00)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.email})"
    
    def check_vip_status(self):
        """Auto-update VIP status based on total spent"""
        if self.total_spent >= self.vip_threshold and not self.is_vip:
            self.is_vip = True
            self.save()
            return True
        elif self.total_spent < self.vip_threshold and self.is_vip:
            self.is_vip = False
            self.save()
            return False
        return self.is_vip

class Agent(models.Model):
    """QuickCart support staff"""
    DEPARTMENT_CHOICES = [
        ('billing', 'Billing'),
        ('tech', 'Technical Support'),
        ('product', 'Product Support'),
        ('general', 'General'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    department = models.CharField(max_length=100, choices=DEPARTMENT_CHOICES, default='general')
    is_senior = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.department}"
    
    @property
    def username(self):
        return self.user.username

class Ticket(models.Model):
    """Customer support ticket"""
    STATUS_CHOICES = [
        ('new', 'New'),
        ('open', 'Open'),
        ('pending', 'Pending'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('chat', 'Chat'),
        ('phone', 'Phone'),
        ('web', 'Web Form'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='tickets')
    assigned_to = models.ForeignKey(Agent, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_tickets')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='email')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Ticket #{self.id}: {self.title}"
    
    def get_variable_context(self):
        """Get all available variables for this ticket"""
        return {
            'customer_name': self.customer.name,
            'customer_email': self.customer.email,
            'ticket_id': self.id,
            'ticket_title': self.title,
            'ticket_status': self.status,
            'ticket_priority': self.priority,
            'agent_name': self.assigned_to.user.username if self.assigned_to else 'Support Agent',
            'organization_name': self.customer.organization.name,
        }

class Conversation(models.Model):
    """Messages between customer and agents"""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='conversations')
    sender_type = models.CharField(max_length=20, choices=[
        ('customer', 'Customer'),
        ('agent', 'Agent'),
    ])
    sender_name = models.CharField(max_length=100, blank=True, help_text="Name of the sender")
    message = models.TextField()
    is_internal_note = models.BooleanField(default=False)
    mentions = models.ManyToManyField(Agent, blank=True, related_name='mentioned_in', 
                                      help_text="Agents mentioned in this note using @username")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message on {self.ticket.id} at {self.created_at}"
    
    def parse_mentions(self):
        """Extract @mentions from message and link to agents"""
        if not self.is_internal_note or self.sender_type != 'agent':
            return []
        
        # Find all @mentions using regex
        pattern = r'@(\w+)'
        usernames = re.findall(pattern, self.message)
        
        if not usernames:
            return []
        
        # Find agents with these usernames in the same organization
        agents = Agent.objects.filter(
            user__username__in=usernames,
            organization=self.ticket.customer.organization
        )
        
        # Add to mentions
        if agents.exists():
            self.mentions.add(*agents)
            
            # Also update the message to highlight mentions (optional)
            for agent in agents:
                self.message = self.message.replace(
                    f"@{agent.user.username}", 
                    f"**@{agent.user.username}**"
                )
            self.save(update_fields=['message'])
        
        return agents
    
    def save(self, *args, **kwargs):
        # Set sender_name automatically
        if self.sender_type == 'agent' and not self.sender_name:
            if hasattr(self, 'ticket') and self.ticket.assigned_to:
                self.sender_name = self.ticket.assigned_to.user.username
            else:
                self.sender_name = 'Unknown Agent'
        elif self.sender_type == 'customer' and not self.sender_name:
            self.sender_name = self.ticket.customer.name
        
        super().save(*args, **kwargs)
        
        # Parse mentions after saving (need ID first)
        if self.is_internal_note and self.sender_type == 'agent':
            self.parse_mentions()

class CannedCategory(models.Model):
    """Categories for organizing canned responses"""
    name = models.CharField(max_length=100)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='canned_categories')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        unique_together = ['name', 'organization']
    
    def __str__(self):
        return self.name

class CannedResponse(models.Model):
    """Pre-written templates for agents with variables"""
    category = models.ForeignKey(CannedCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='canned_responses')
    title = models.CharField(max_length=100)
    shortcode = models.CharField(max_length=50, help_text="e.g., #refund, #tracking")
    content = models.TextField(help_text="Use {{variable}} syntax. Available: customer_name, order_number, etc.")
    variables = models.JSONField(default=list, blank=True, help_text="List of variables used in this template")
    department = models.CharField(max_length=50, blank=True, help_text="Leave blank for all departments")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='canned_responses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    usage_count = models.IntegerField(default=0, help_text="How many times this template has been used")
    
    class Meta:
        ordering = ['category__name', 'title']
        unique_together = ['shortcode', 'organization']
    
    def __str__(self):
        return f"{self.shortcode} - {self.title}"
    
    def extract_variables(self):
        """Extract variable names from content (e.g., {{customer_name}} -> customer_name)"""
        import re
        pattern = r'\{\{([^}]+)\}\}'
        variables = re.findall(pattern, self.content)
        # Remove duplicates and strip whitespace
        variables = list(set([v.strip() for v in variables]))
        self.variables = variables
        self.save(update_fields=['variables'])
        return variables
    
    def render(self, context):
        """Replace variables in content with actual values from context"""
        rendered = self.content
        for var in self.variables:
            value = context.get(var, f'[{var} not found]')
            rendered = rendered.replace(f'{{{{{var}}}}}', str(value))
        return rendered
    
    def preview(self, sample_data=None):
        """Show preview with sample data"""
        if sample_data is None:
            # Default sample data for preview
            sample_data = {
                'customer_name': 'John Doe',
                'order_number': 'ORD-12345',
                'order_status': 'shipped',
                'tracking_link': 'https://track.com/12345',
                'agent_name': 'Support Agent',
                'ticket_id': '123',
                'organization_name': 'QuickCart'
            }
        return self.render(sample_data)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

class RoutingRule(models.Model):
    """Automatically route tickets based on keywords"""
    CONDITION_CHOICES = [
        ('contains', 'Contains'),
        ('equals', 'Equals'),
        ('starts_with', 'Starts With'),
    ]
    
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='routing_rules')
    name = models.CharField(max_length=100, help_text="e.g., 'Billing Questions'")
    keywords = models.TextField(help_text="Comma-separated keywords: refund, money, charge")
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='contains')
    department = models.CharField(max_length=50, choices=Agent.DEPARTMENT_CHOICES)
    priority = models.CharField(max_length=20, choices=Ticket.PRIORITY_CHOICES, default='medium')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.department})"
    
    def get_keywords_list(self):
        """Convert comma-separated keywords to list"""
        return [k.strip().lower() for k in self.keywords.split(',')]


class TicketAttachment(models.Model):
    """Files attached to tickets"""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='ticket_attachments/%Y/%m/%d/')
    filename = models.CharField(max_length=255, blank=True)
    file_size = models.IntegerField(blank=True, null=True, help_text="Size in bytes")
    uploaded_by = models.CharField(max_length=50, choices=[
        ('customer', 'Customer'),
        ('agent', 'Agent'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if self.file and not self.filename:
            self.filename = self.file.name
        if self.file and not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.filename} for Ticket #{self.ticket.id}"
    

class KnowledgeCategory(models.Model):
    """Categories for knowledge base articles"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='kb_categories')
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon name")
    display_order = models.IntegerField(default=0)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['display_order', 'name']
        verbose_name_plural = "Knowledge categories"
    
    def __str__(self):
        return self.name

class KnowledgeArticle(models.Model):
    """Knowledge base articles for customer self-service"""
    category = models.ForeignKey(KnowledgeCategory, on_delete=models.CASCADE, related_name='articles')
    title = models.CharField(max_length=200)
    content = models.TextField()
    summary = models.TextField(max_length=500, blank=True, help_text="Short summary for search results")
    
    # Metadata
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='kb_articles')
    author = models.ForeignKey(Agent, null=True, blank=True, on_delete=models.SET_NULL)
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    
    # Status
    is_published = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True, help_text="Public articles visible to all customers")
    is_featured = models.BooleanField(default=False)
    
    # Metrics
    views = models.IntegerField(default=0)
    helpful_count = models.IntegerField(default=0)
    not_helpful_count = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-is_featured', '-views', '-created_at']
        indexes = [
            models.Index(fields=['organization', 'is_published']),
            models.Index(fields=['organization', 'category']),
        ]
    
    def __str__(self):
        return self.title
    
    def get_tags_list(self):
        """Return tags as list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []
    
    def helpful_percentage(self):
        """Calculate helpful percentage"""
        total = self.helpful_count + self.not_helpful_count
        if total == 0:
            return 0
        return round((self.helpful_count / total) * 100)
    
    def increment_views(self):
        """Increment view count"""
        self.views += 1
        self.save(update_fields=['views'])

class ArticleFeedback(models.Model):
    """Track user feedback on articles"""
    article = models.ForeignKey(KnowledgeArticle, on_delete=models.CASCADE, related_name='feedback')
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL)
    session_id = models.CharField(max_length=100, blank=True, help_text="For anonymous users")
    is_helpful = models.BooleanField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Feedback on {self.article.title}: {'👍' if self.is_helpful else '👎'}"