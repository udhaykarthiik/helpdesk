from rest_framework import serializers
from .models import Organization, Customer, Agent, Ticket, Conversation, CannedCategory, CannedResponse, RoutingRule, TicketAttachment, KnowledgeCategory, KnowledgeArticle, ArticleFeedback

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'phone', 'organization', 'total_spent', 
                  'is_vip', 'vip_threshold', 'created_at']

class AgentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = Agent
        fields = ['id', 'username', 'email', 'department', 'is_senior', 'organization', 'created_at']

class TicketAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_size_display = serializers.SerializerMethodField()
    
    class Meta:
        model = TicketAttachment
        fields = ['id', 'ticket', 'filename', 'file_url', 'file_size', 'file_size_display', 'uploaded_by', 'created_at']
        read_only_fields = ['filename', 'file_size']
    
    def get_file_url(self, obj):
        request = self.context.get('request')
        if request and obj.file:
            return request.build_absolute_uri(obj.file.url)
        return None
    
    def get_file_size_display(self, obj):
        """Convert bytes to human readable format"""
        size = obj.file_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size/1024:.1f} KB"
        else:
            return f"{size/(1024*1024):.1f} MB"

class ConversationSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    mentioned_agents = serializers.SerializerMethodField()
    attachments = TicketAttachmentSerializer(many=True, read_only=True, source='ticket.attachments')
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'ticket', 'sender_type', 'sender_name', 'message', 
            'is_internal_note', 'mentions', 'mentioned_agents', 'attachments', 'created_at'
        ]
        read_only_fields = ['mentions']
    
    def get_sender_name(self, obj):
        if obj.sender_name:
            return obj.sender_name
        if obj.sender_type == 'customer':
            return obj.ticket.customer.name
        else:
            return obj.ticket.assigned_to.user.username if obj.ticket.assigned_to else 'Unknown Agent'
    
    def get_mentioned_agents(self, obj):
        """Return list of mentioned agents with details"""
        if obj.mentions.exists():
            return [
                {
                    'id': agent.id,
                    'username': agent.user.username,
                    'email': agent.user.email,
                    'department': agent.department
                }
                for agent in obj.mentions.all()
            ]
        return []

class TicketSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    customer_is_vip = serializers.BooleanField(source='customer.is_vip', read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    conversations = ConversationSerializer(many=True, read_only=True)
    attachments = TicketAttachmentSerializer(many=True, read_only=True)
    available_variables = serializers.SerializerMethodField()
    mention_count = serializers.SerializerMethodField()
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)
    
    class Meta:
        model = Ticket
        fields = [
            'id', 'title', 'description', 'customer', 'customer_name', 'customer_email', 'customer_is_vip',
            'assigned_to', 'assigned_to_name', 'status', 'priority', 'channel', 'channel_display',
            'created_at', 'updated_at', 'resolved_at', 'conversations', 'attachments', 
            'available_variables', 'mention_count'
        ]
    
    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.user.username
        return None
    
    def get_available_variables(self, obj):
        """Return all variables available for this ticket"""
        return obj.get_variable_context()
    
    def get_mention_count(self, obj):
        """Count how many mentions this ticket has"""
        return Conversation.objects.filter(
            ticket=obj,
            is_internal_note=True,
            mentions__isnull=False
        ).count()

class PublicTicketSerializer(serializers.ModelSerializer):
    """Simplified serializer for public ticket creation"""
    customer_email = serializers.EmailField(write_only=True)
    customer_name = serializers.CharField(write_only=True)
    
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'customer_email', 'customer_name', 'channel']
        extra_kwargs = {
            'channel': {'read_only': True}
        }
    
    def create(self, validated_data):
        customer_email = validated_data.pop('customer_email')
        customer_name = validated_data.pop('customer_name')
        
        # Get or create customer
        organization = Organization.objects.first()  # Assuming QuickCart is first org
        customer, created = Customer.objects.get_or_create(
            email=customer_email,
            defaults={
                'name': customer_name,
                'organization': organization
            }
        )
        
        # Create ticket
        ticket = Ticket.objects.create(
            customer=customer,
            channel='web',  # Mark as web form submission
            **validated_data
        )
        
        return ticket

class CannedCategorySerializer(serializers.ModelSerializer):
    response_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CannedCategory
        fields = ['id', 'name', 'organization', 'description', 'response_count', 'created_at']
    
    def get_response_count(self, obj):
        return obj.canned_responses.count()

class CannedResponseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    preview = serializers.SerializerMethodField()
    
    class Meta:
        model = CannedResponse
        fields = [
            'id', 'title', 'shortcode', 'content', 'variables', 'category', 'category_name',
            'department', 'organization', 'usage_count', 'created_at', 'updated_at', 'preview'
        ]
        read_only_fields = ['variables', 'usage_count']
    
    def get_preview(self, obj):
        """Generate preview with sample data"""
        return obj.preview()

class CannedResponseRenderSerializer(serializers.Serializer):
    """Serializer for rendering a canned response with actual data"""
    ticket_id = serializers.IntegerField(required=True)
    canned_response_id = serializers.IntegerField(required=True)
    
    def validate(self, data):
        """Validate that both ticket and canned response exist"""
        try:
            ticket = Ticket.objects.get(id=data['ticket_id'])
            canned = CannedResponse.objects.get(id=data['canned_response_id'])
            data['ticket'] = ticket
            data['canned'] = canned
        except Ticket.DoesNotExist:
            raise serializers.ValidationError({"ticket_id": "Ticket not found"})
        except CannedResponse.DoesNotExist:
            raise serializers.ValidationError({"canned_response_id": "Canned response not found"})
        return data
    
    def get_rendered_content(self):
        """Render the canned response with ticket data"""
        ticket = self.validated_data['ticket']
        canned = self.validated_data['canned']
        
        # Increment usage count
        canned.usage_count += 1
        canned.save(update_fields=['usage_count'])
        
        # Render with ticket context
        context = ticket.get_variable_context()
        rendered = canned.render(context)
        
        return {
            'rendered_content': rendered,
            'variables_used': canned.variables,
            'ticket_id': ticket.id,
            'canned_title': canned.title,
            'usage_count': canned.usage_count
        }

class RoutingRuleSerializer(serializers.ModelSerializer):
    department_display = serializers.CharField(source='get_department_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = RoutingRule
        fields = ['id', 'name', 'keywords', 'condition', 'department', 'department_display', 
                  'priority', 'priority_display', 'is_active', 'organization', 'created_at']
        
class KnowledgeCategorySerializer(serializers.ModelSerializer):
    article_count = serializers.SerializerMethodField()
    
    class Meta:
        model = KnowledgeCategory
        fields = ['id', 'name', 'description', 'organization', 'icon', 'display_order', 
                  'is_public', 'article_count', 'created_at']
    
    def get_article_count(self, obj):
        return obj.articles.filter(is_published=True).count()

class KnowledgeArticleSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    author_name = serializers.SerializerMethodField()
    tags_list = serializers.SerializerMethodField()
    helpful_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = KnowledgeArticle
        fields = [
            'id', 'title', 'summary', 'content', 'category', 'category_name',
            'organization', 'author', 'author_name', 'tags', 'tags_list',
            'is_published', 'is_public', 'is_featured',
            'views', 'helpful_count', 'not_helpful_count', 'helpful_percentage',
            'created_at', 'updated_at', 'published_at'
        ]
        read_only_fields = ['views', 'helpful_count', 'not_helpful_count']
    
    def get_author_name(self, obj):
        if obj.author:
            return obj.author.user.username
        return None
    
    def get_tags_list(self, obj):
        return obj.get_tags_list()
    
    def get_helpful_percentage(self, obj):
        return obj.helpful_percentage()

class PublicKnowledgeArticleSerializer(serializers.ModelSerializer):
    """Simplified serializer for public view (no internal fields)"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    tags_list = serializers.SerializerMethodField()
    
    class Meta:
        model = KnowledgeArticle
        fields = [
            'id', 'title', 'summary', 'content', 'category_name', 'tags_list',
            'views', 'helpful_percentage', 'created_at', 'updated_at'
        ]
        read_only_fields = ['views', 'helpful_percentage']
    
    def get_tags_list(self, obj):
        return obj.get_tags_list()

class ArticleFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleFeedback
        fields = ['id', 'article', 'customer', 'session_id', 'is_helpful', 'comment', 'created_at']
        read_only_fields = ['created_at']