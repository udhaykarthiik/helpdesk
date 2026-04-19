from django.contrib import admin
from .models import Organization, Customer, Agent, Ticket, Conversation, CannedCategory, CannedResponse, RoutingRule
from django.utils import timezone
from .models import Organization, Customer, Agent, Ticket, Conversation, CannedCategory, CannedResponse, RoutingRule, KnowledgeCategory, KnowledgeArticle, ArticleFeedback
from .models import TicketAttachment

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')
    search_fields = ('name',)

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'phone', 'is_vip', 'total_spent', 'vip_threshold', 'created_at')
    list_filter = ('is_vip', 'organization')
    search_fields = ('name', 'email', 'phone')
    list_editable = ('is_vip', 'vip_threshold')
    fieldsets = (
        (None, {
            'fields': ('name', 'email', 'phone', 'organization')
        }),
        ('VIP Settings', {
            'fields': ('total_spent', 'vip_threshold', 'is_vip'),
            'classes': ('wide',)
        }),
    )

@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'department', 'is_senior', 'organization')
    list_filter = ('department', 'is_senior', 'organization')
    search_fields = ('user__username', 'user__email')

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'customer', 'assigned_to', 'status', 'priority', 'channel', 'created_at')
    list_filter = ('status', 'priority', 'channel', 'created_at')
    search_fields = ('title', 'description', 'customer__name', 'customer__email')
    list_editable = ('status', 'priority', 'assigned_to')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'customer')
        }),
        ('Assignment & Status', {
            'fields': ('assigned_to', 'status', 'priority', 'channel')
        }),
        ('Timestamps', {
            'fields': ('resolved_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['show_variable_context']
    
    def show_variable_context(self, request, queryset):
        """Show available variables for selected tickets"""
        for ticket in queryset:
            context = ticket.get_variable_context()
            self.message_user(request, f"Ticket #{ticket.id} variables: {', '.join(context.keys())}")
    show_variable_context.short_description = "Show available variables"

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'sender_type', 'is_internal_note', 'created_at')
    list_filter = ('sender_type', 'is_internal_note', 'created_at')
    search_fields = ('message', 'ticket__title')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('ticket')

@admin.register(CannedCategory)
class CannedCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'organization', 'description', 'created_at')
    list_filter = ('organization',)
    search_fields = ('name', 'description')
    list_editable = ('name',)

@admin.register(CannedResponse)
class CannedResponseAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'shortcode', 'category', 'department', 'usage_count', 'organization', 'created_at')
    list_filter = ('category', 'department', 'organization')
    search_fields = ('title', 'shortcode', 'content')
    list_editable = ('shortcode', 'category', 'department')
    autocomplete_fields = ('category',)
    readonly_fields = ('variables', 'usage_count', 'extracted_variables_display', 'preview_display')
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'shortcode', 'category', 'department', 'organization')
        }),
        ('Content', {
            'fields': ('content',),
            'description': 'Use {{variable_name}} syntax. Example: Hello {{customer_name}}, your order #{{order_number}} is {{status}}.'
        }),
        ('Auto-generated', {
            'fields': ('variables', 'usage_count', 'extracted_variables_display', 'preview_display'),
            'classes': ('collapse',)
        }),
    )
    
    def extracted_variables_display(self, obj):
        """Show extracted variables"""
        if obj.pk:
            vars = obj.extract_variables()
            return ', '.join(vars) if vars else 'No variables found'
        return 'Save to extract variables'
    extracted_variables_display.short_description = 'Detected Variables'
    
    def preview_display(self, obj):
        """Show preview with sample data"""
        if obj.pk:
            preview = obj.preview()
            return f'<div style="background:#f8f9fa; padding:10px; border:1px solid #ddd;">{preview}</div>'
        return 'Save to see preview'
    preview_display.short_description = 'Preview'
    preview_display.allow_tags = True
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.extract_variables()

@admin.register(RoutingRule)
class RoutingRuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'department', 'priority', 'is_active', 'organization')
    list_filter = ('department', 'priority', 'is_active', 'organization')
    search_fields = ('name', 'keywords')
    list_editable = ('is_active', 'priority')


@admin.register(KnowledgeCategory)
class KnowledgeCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'organization', 'article_count', 'is_public', 'display_order')
    list_filter = ('organization', 'is_public')
    search_fields = ('name', 'description')
    list_editable = ('display_order', 'is_public')
    
    def article_count(self, obj):
        return obj.articles.count()
    article_count.short_description = 'Articles'

@admin.register(KnowledgeArticle)
class KnowledgeArticleAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'is_published', 'is_public', 'is_featured', 'views', 'helpful_percentage_display', 'created_at')
    list_filter = ('category', 'is_published', 'is_public', 'is_featured', 'organization')
    search_fields = ('title', 'content', 'summary', 'tags')
    list_editable = ('is_published', 'is_public', 'is_featured')
    readonly_fields = ('views', 'helpful_count', 'not_helpful_count', 'helpful_percentage_display', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'summary', 'content', 'category', 'organization')
        }),
        ('Metadata', {
            'fields': ('author', 'tags', 'is_published', 'is_public', 'is_featured')
        }),
        ('Statistics', {
            'fields': ('views', 'helpful_count', 'not_helpful_count', 'helpful_percentage_display'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('published_at',),  # Removed created_at and updated_at from here
            'classes': ('collapse',)
        }),
    )
    
    def helpful_percentage_display(self, obj):
        percentage = obj.helpful_percentage()
        return f"{percentage}% ({obj.helpful_count}👍 / {obj.not_helpful_count}👎)"
    helpful_percentage_display.short_description = 'Helpful %'
    
    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            try:
                obj.author = Agent.objects.get(user=request.user)
            except Agent.DoesNotExist:
                pass
        if obj.is_published and not obj.published_at:
            obj.published_at = timezone.now()
        super().save_model(request, obj, form, change)

@admin.register(ArticleFeedback)
class ArticleFeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'article', 'is_helpful', 'customer', 'session_id', 'created_at')
    list_filter = ('is_helpful', 'created_at')
    search_fields = ('article__title', 'comment', 'customer__email')
    readonly_fields = ('created_at',)

@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'filename', 'file_size', 'uploaded_by', 'created_at')
    list_filter = ('uploaded_by', 'created_at')
    search_fields = ('filename', 'ticket__title')
    readonly_fields = ('filename', 'file_size', 'created_at')