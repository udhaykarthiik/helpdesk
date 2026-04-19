from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q, Count
from django.utils import timezone
from django.conf import settings
import os
import re

from .models import Organization, Customer, Agent, Ticket, Conversation, CannedCategory, CannedResponse, RoutingRule, TicketAttachment, KnowledgeCategory, KnowledgeArticle, ArticleFeedback

from .serializers import (
    OrganizationSerializer, CustomerSerializer, AgentSerializer,
    TicketSerializer, ConversationSerializer, CannedCategorySerializer,
    CannedResponseSerializer, CannedResponseRenderSerializer, RoutingRuleSerializer,
    TicketAttachmentSerializer, PublicTicketSerializer,
    KnowledgeCategorySerializer, KnowledgeArticleSerializer, 
    PublicKnowledgeArticleSerializer, ArticleFeedbackSerializer
)
from .ai_services import classify_ticket, generate_canned_response, check_ai_health
from .email_utils import send_ticket_confirmation, send_reply_notification
from .order_utils import check_order_auto_response

class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    
    @action(detail=True, methods=['get'])
    def tickets(self, request, pk=None):
        customer = self.get_object()
        tickets = Ticket.objects.filter(customer=customer).order_by('-created_at')
        serializer = TicketSerializer(tickets, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def check_vip(self, request, pk=None):
        """Manually trigger VIP status check"""
        customer = self.get_object()
        old_status = customer.is_vip
        new_status = customer.check_vip_status()
        
        return Response({
            "customer_id": customer.id,
            "name": customer.name,
            "old_vip_status": old_status,
            "new_vip_status": new_status,
            "total_spent": str(customer.total_spent),
            "threshold": str(customer.vip_threshold)
        })

class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    
    def get_queryset(self):
        queryset = Agent.objects.all()
        org_id = self.request.query_params.get('organization', None)
        if org_id:
            queryset = queryset.filter(organization_id=org_id)
        return queryset
    
    @action(detail=False, methods=['get'])
    def by_department(self, request):
        department = request.query_params.get('department', None)
        org_id = request.query_params.get('organization', 1)
        
        if department:
            agents = Agent.objects.filter(department=department, organization_id=org_id)
            serializer = self.get_serializer(agents, many=True)
            return Response(serializer.data)
        return Response({"error": "Department parameter required"}, status=400)
    
    @action(detail=True, methods=['get'])
    def mentions(self, request, pk=None):
        """Get all tickets where this agent was mentioned"""
        agent = self.get_object()
        conversations = Conversation.objects.filter(
            mentions=agent,
            is_internal_note=True
        ).select_related('ticket').order_by('-created_at')
        
        tickets = []
        for conv in conversations:
            tickets.append({
                'ticket_id': conv.ticket.id,
                'ticket_title': conv.ticket.title,
                'mentioned_by': conv.sender_name,
                'mentioned_at': conv.created_at,
                'message': conv.message[:100] + '...' if len(conv.message) > 100 else conv.message,
                'ticket_status': conv.ticket.status,
                'ticket_priority': conv.ticket.priority
            })
        
        return Response({
            'agent': agent.user.username,
            'total_mentions': conversations.count(),
            'mentions': tickets
        })

class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all().order_by('-created_at')
    serializer_class = TicketSerializer
    
    def get_queryset(self):
        queryset = Ticket.objects.all().order_by('-created_at')
        
        # Filter by status
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by priority
        priority = self.request.query_params.get('priority', None)
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Filter by assigned agent
        assigned = self.request.query_params.get('assigned', None)
        if assigned:
            if assigned == 'unassigned':
                queryset = queryset.filter(assigned_to__isnull=True)
            else:
                queryset = queryset.filter(assigned_to=assigned)
        
        # Filter by VIP
        vip = self.request.query_params.get('vip', None)
        if vip == 'true':
            queryset = queryset.filter(customer__is_vip=True)
        elif vip == 'false':
            queryset = queryset.filter(customer__is_vip=False)
        
        # Filter by channel
        channel = self.request.query_params.get('channel', None)
        if channel:
            queryset = queryset.filter(channel=channel)
        
        # Filter by mentions
        mentioned = self.request.query_params.get('mentioned', None)
        if mentioned:
            queryset = queryset.filter(
                conversations__mentions__isnull=False,
                conversations__is_internal_note=True
            ).distinct()
        
        return queryset
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def apply_routing_rules(self, ticket):
        """Auto-assign ticket based on keywords"""
        rules = RoutingRule.objects.filter(
            organization=ticket.customer.organization,
            is_active=True
        )
        
        for rule in rules:
            ticket_text = f"{ticket.title} {ticket.description}".lower()
            
            for keyword in rule.get_keywords_list():
                if keyword in ticket_text:
                    ticket.priority = rule.priority
                    
                    agent = Agent.objects.filter(
                        organization=ticket.customer.organization,
                        department=rule.department
                    ).first()
                    
                    if agent:
                        ticket.assigned_to = agent
                        ticket.status = 'open'
                    
                    ticket.save()
                    
                    Conversation.objects.create(
                        ticket=ticket,
                        sender_type='agent',
                        message=f"[SYSTEM] Auto-routed to {rule.department} department based on keyword: '{keyword}'",
                        is_internal_note=True
                    )
                    return True
        
        return False
    
    def apply_vip_handling(self, ticket):
        """Apply VIP benefits to ticket if customer is VIP"""
        customer = ticket.customer
        
        was_vip = customer.is_vip
        customer.check_vip_status()
        
        if customer.is_vip:
            if ticket.priority == 'low':
                ticket.priority = 'medium'
            elif ticket.priority == 'medium':
                ticket.priority = 'high'
            elif ticket.priority == 'high':
                ticket.priority = 'urgent'
            
            if not ticket.assigned_to:
                senior_agent = Agent.objects.filter(
                    organization=customer.organization,
                    is_senior=True
                ).first()
                if senior_agent:
                    ticket.assigned_to = senior_agent
                    ticket.status = 'open'
            
            ticket.save()
            
            if not was_vip and customer.is_vip:
                Conversation.objects.create(
                    ticket=ticket,
                    sender_type='agent',
                    message="[SYSTEM] Customer automatically upgraded to VIP based on total spending.",
                    is_internal_note=True
                )
            elif was_vip and customer.is_vip:
                Conversation.objects.create(
                    ticket=ticket,
                    sender_type='agent',
                    message=f"[SYSTEM] VIP customer - Priority boosted to {ticket.priority}",
                    is_internal_note=True
                )
            
            return True
        return False
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # ========== NEW: Check for order status query ==========
        ticket_data = request.data.copy()
        
        # Try to auto-respond to order queries
        temp_ticket = Ticket(
            title=ticket_data.get('title', ''),
            description=ticket_data.get('description', ''),
            customer_id=ticket_data.get('customer', 1)  # Temporary for checking
        )
        
        auto_responded, auto_response = check_order_auto_response(temp_ticket)
        # ======================================================
        
        # Get AI analysis (optional)
        try:
            ai_analysis = classify_ticket(
                request.data.get('title', ''),
                request.data.get('description', '')
            )
            
            # Auto-apply AI suggestions
            ticket_data = {
                **request.data,
                'priority': ai_analysis.get('priority', request.data.get('priority', 'medium')),
            }
            
            # If needs escalation, set high priority
            if ai_analysis.get('needs_escalation'):
                ticket_data['priority'] = 'urgent'
            
            serializer = self.get_serializer(data=ticket_data)
            serializer.is_valid(raise_exception=True)
            ticket = serializer.save()
            
            # Add AI analysis as internal note
            Conversation.objects.create(
                ticket=ticket,
                sender_type='agent',
                message=f"[AI ANALYSIS] Category: {ai_analysis.get('category', 'unknown')}, "
                        f"Sentiment: {ai_analysis.get('sentiment', 'unknown')}, "
                        f"Summary: {ai_analysis.get('summary', '')}",
                is_internal_note=True
            )
        except Exception as e:
            # If AI fails, still create ticket normally
            print(f"AI analysis failed: {e}")
            ticket = serializer.save()
        
        # ========== NEW: Add auto-response if order query detected ==========
        if auto_responded:
            Conversation.objects.create(
                ticket=ticket,
                sender_type='agent',
                message=auto_response,
                is_internal_note=False
            )
            print(f"🤖 Auto-responded to order query for ticket #{ticket.id}")
        # ====================================================================
        
        # Send email confirmation
        try:
            from .email_utils import send_ticket_confirmation
            send_ticket_confirmation(ticket)
        except Exception as e:
            print(f"Email sending failed: {e}")
        
        self.apply_routing_rules(ticket)
        self.apply_vip_handling(ticket)
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Public endpoint to check ticket status - no login required"""
        try:
            ticket = self.get_object()
            email = request.query_params.get('email')
            
            # Verify email matches ticket customer
            if not email or ticket.customer.email != email:
                return Response(
                    {"error": "Invalid email or ticket ID"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Return ticket with conversations
            serializer = TicketSerializer(ticket, context={'request': request})
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {"error": "Ticket not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    # ========== PUBLIC FORM (NO LOGIN REQUIRED) ==========
    
    @action(detail=False, methods=['post'], authentication_classes=[], permission_classes=[])
    def public_create(self, request):
        """Public endpoint for customers to create tickets without login"""
        
        # Rate limiting
        recent_tickets = Ticket.objects.filter(
            customer__email=request.data.get('customer_email'),
            created_at__gte=timezone.now() - timezone.timedelta(hours=1)
        ).count()
        
        if recent_tickets >= 3:
            return Response({
                "error": "Too many tickets from this email. Please wait."
            }, status=429)
        
        # Validate email format
        email = request.data.get('customer_email', '')
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return Response({"error": "Invalid email format"}, status=400)
        
        # Spam check
        spam_keywords = ['viagra', 'casino', 'lottery', 'porn', 'sex', 'gambling']
        content = f"{request.data.get('title', '')} {request.data.get('description', '')}".lower()
        if any(keyword in content for keyword in spam_keywords):
            return Response({"error": "Content flagged as spam"}, status=400)
        
        # ========== NEW: Check for order status query BEFORE creating ==========
        temp_ticket = Ticket(
            title=request.data.get('title', ''),
            description=request.data.get('description', ''),
            customer_id=1  # Temporary
        )
        auto_responded, auto_response = check_order_auto_response(temp_ticket)
        # =======================================================================
        
        serializer = PublicTicketSerializer(data=request.data)
        if serializer.is_valid():
            ticket = serializer.save()
            
            # Create auto-response in conversation
            Conversation.objects.create(
                ticket=ticket,
                sender_type='agent',
                message=f"Thank you for contacting support. Your ticket #{ticket.id} has been created. We'll respond within 24 hours.",
                is_internal_note=False
            )
            
            # ========== NEW: Add auto-response if order query detected ==========
            if auto_responded:
                Conversation.objects.create(
                    ticket=ticket,
                    sender_type='agent',
                    message=auto_response,
                    is_internal_note=False
                )
                print(f"🤖 Auto-responded to order query for public ticket #{ticket.id}")
            # ====================================================================
            
            # Send email confirmation
            try:
                from .email_utils import send_ticket_confirmation
                send_ticket_confirmation(ticket)
            except Exception as e:
                print(f"Email sending failed: {e}")
            
            return Response({
                'success': True,
                'ticket_id': ticket.id,
                'message': 'Your ticket has been created. Check your email for confirmation.',
                'auto_responded': auto_responded
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # ========== ATTACHMENT HANDLING ==========
    
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def add_attachment(self, request, pk=None):
        """Add attachment to existing ticket"""
        ticket = self.get_object()
        file_obj = request.FILES.get('file')
        uploaded_by = request.data.get('uploaded_by', 'agent')
        
        if not file_obj:
            return Response({"error": "No file provided"}, status=400)
        
        # Check file size (limit 5MB)
        if file_obj.size > 5 * 1024 * 1024:
            return Response({"error": "File size exceeds 5MB limit"}, status=400)
        
        # Check file type (optional)
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf', 'text/plain']
        if file_obj.content_type not in allowed_types:
            return Response({"error": f"File type not allowed. Allowed: {allowed_types}"}, status=400)
        
        attachment = TicketAttachment.objects.create(
            ticket=ticket,
            file=file_obj,
            filename=file_obj.name,
            file_size=file_obj.size,
            uploaded_by=uploaded_by
        )
        
        serializer = TicketAttachmentSerializer(attachment, context={'request': request})
        return Response(serializer.data, status=201)
    
    @action(detail=True, methods=['get'])
    def attachments(self, request, pk=None):
        """Get all attachments for a ticket"""
        ticket = self.get_object()
        attachments = ticket.attachments.all()
        serializer = TicketAttachmentSerializer(attachments, many=True, context={'request': request})
        return Response(serializer.data)
    
    # ========== EXISTING ACTIONS ==========
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        ticket = self.get_object()
        agent_id = request.data.get('agent_id')
        
        if not agent_id:
            return Response({"error": "agent_id required"}, status=400)
        
        try:
            agent = Agent.objects.get(id=agent_id)
            old_assignee = ticket.assigned_to
            ticket.assigned_to = agent
            ticket.status = 'open'
            ticket.save()
            
            Conversation.objects.create(
                ticket=ticket,
                sender_type='agent',
                message=f"[SYSTEM] Ticket assigned to {agent.user.username}",
                is_internal_note=True
            )
            
            return Response({
                "status": "assigned", 
                "agent": agent.user.username,
                "previous_assignee": old_assignee.user.username if old_assignee else None
            })
        except Agent.DoesNotExist:
            return Response({"error": "Agent not found"}, status=404)
    
    @action(detail=True, methods=['post'])  
    def add_conversation(self, request, pk=None):
        ticket = self.get_object()
        
        conversation = Conversation.objects.create(
            ticket=ticket,
            sender_type=request.data.get('sender_type', 'agent'),
            message=request.data['message'],
            is_internal_note=request.data.get('is_internal_note', False)
        )
    
        # ========== SEND EMAIL IF IT'S AN AGENT REPLY (NOT INTERNAL NOTE) ==========
        if conversation.sender_type == 'agent' and not conversation.is_internal_note:
            try:
                from .email_utils import send_reply_notification
                send_reply_notification(ticket, conversation)
            except Exception as e:
                print(f"Reply email sending failed: {e}")
        # ============================================================================
        
        serializer = ConversationSerializer(conversation, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    

    @action(detail=True, methods=['get'])
    def conversations(self, request, pk=None):
        ticket = self.get_object()
        conversations = Conversation.objects.filter(ticket=ticket).order_by('created_at')
        serializer = ConversationSerializer(conversations, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        ticket = self.get_object()
        ticket.status = 'resolved'
        ticket.resolved_at = timezone.now()
        ticket.save()
        
        Conversation.objects.create(
            ticket=ticket,
            sender_type='agent',
            message="[SYSTEM] Ticket marked as resolved",
            is_internal_note=True
        )
        
        return Response({"status": "resolved"})
    
    @action(detail=True, methods=['post'])
    def reroute(self, request, pk=None):
        ticket = self.get_object()
        applied = self.apply_routing_rules(ticket)
        if applied:
            return Response({"status": "rerouted", "ticket": TicketSerializer(ticket, context={'request': request}).data})
        return Response({"status": "no rules applied", "ticket": TicketSerializer(ticket, context={'request': request}).data})
    
    @action(detail=True, methods=['post'])
    def check_vip(self, request, pk=None):
        ticket = self.get_object()
        applied = self.apply_vip_handling(ticket)
        return Response({
            "status": "vip_handling_applied" if applied else "not_vip",
            "ticket": TicketSerializer(ticket, context={'request': request}).data
        })
    
    # ========== QUICK ACTIONS ==========
    
    @action(detail=True, methods=['post'])
    def quick_resolve(self, request, pk=None):
        ticket = self.get_object()
        old_status = ticket.status
        ticket.status = 'resolved'
        ticket.resolved_at = timezone.now()
        ticket.save()
        
        Conversation.objects.create(
            ticket=ticket,
            sender_type='agent',
            message=f"[SYSTEM] Ticket resolved by {request.user.username if request.user.is_authenticated else 'Agent'}",
            is_internal_note=True
        )
        
        return Response({
            "status": "resolved",
            "ticket_id": ticket.id,
            "previous_status": old_status
        })
    
    @action(detail=True, methods=['post'])
    def quick_assign_to_me(self, request, pk=None):
        ticket = self.get_object()
        
        try:
            agent = Agent.objects.get(user=request.user)
            old_assignee = ticket.assigned_to
            ticket.assigned_to = agent
            ticket.status = 'open'
            ticket.save()
            
            Conversation.objects.create(
                ticket=ticket,
                sender_type='agent',
                message=f"[SYSTEM] Ticket assigned to {agent.user.username}",
                is_internal_note=True
            )
            
            return Response({
                "status": "assigned",
                "ticket_id": ticket.id,
                "assigned_to": agent.user.username,
                "previous_assignee": old_assignee.user.username if old_assignee else None
            })
        except Agent.DoesNotExist:
            return Response({"error": "You are not registered as an agent"}, status=400)
    
    @action(detail=True, methods=['post'])
    def quick_status_change(self, request, pk=None):
        ticket = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(Ticket.STATUS_CHOICES):
            return Response({"error": f"Invalid status. Choose from: {list(dict(Ticket.STATUS_CHOICES).keys())}"}, status=400)
        
        old_status = ticket.status
        ticket.status = new_status
        
        if new_status == 'resolved':
            ticket.resolved_at = timezone.now()
        
        ticket.save()
        
        Conversation.objects.create(
            ticket=ticket,
            sender_type='agent',
            message=f"[SYSTEM] Status changed from {old_status} to {new_status} by {request.user.username if request.user.is_authenticated else 'Agent'}",
            is_internal_note=True
        )
        
        return Response({
            "status": "updated",
            "ticket_id": ticket.id,
            "old_status": old_status,
            "new_status": new_status
        })
    

    @action(detail=True, methods=['post'])
    def quick_note(self, request, pk=None):
        ticket = self.get_object()
        note = request.data.get('note')
        
        if not note:
            return Response({"error": "note is required"}, status=400)
        
        conversation = Conversation.objects.create(
            ticket=ticket,
            sender_type='agent',
            message=note,
            is_internal_note=True  # Quick notes are always internal
        )
        
        # Quick notes are internal, so NO EMAIL sent
        
        mentioned = conversation.mentions.all()
        
        return Response({
            "status": "note_added",
            "note_id": conversation.id,
            "message": "Internal note added successfully",
            "mentions": [agent.user.username for agent in mentioned] if mentioned else []
        })
    
    @action(detail=True, methods=['get'])
    def quick_summary(self, request, pk=None):
        ticket = self.get_object()
        
        recent = ticket.conversations.order_by('-created_at')[:3]
        now = timezone.now()
        age_hours = (now - ticket.created_at).total_seconds() / 3600
        
        mentions = Conversation.objects.filter(
            ticket=ticket,
            is_internal_note=True,
            mentions__isnull=False
        ).count()
        
        attachments_count = ticket.attachments.count()
        
        return Response({
            "ticket_id": ticket.id,
            "title": ticket.title,
            "customer": ticket.customer.name,
            "customer_email": ticket.customer.email,
            "customer_vip": ticket.customer.is_vip,
            "status": ticket.status,
            "priority": ticket.priority,
            "channel": ticket.channel,
            "age_hours": round(age_hours, 1),
            "assigned_to": ticket.assigned_to.user.username if ticket.assigned_to else None,
            "total_mentions": mentions,
            "total_attachments": attachments_count,
            "recent_activity": [
                {
                    "type": "note" if c.is_internal_note else "message",
                    "from": c.sender_name,
                    "time": c.created_at,
                    "preview": c.message[:50] + "..." if len(c.message) > 50 else c.message,
                    "mentions": [agent.user.username for agent in c.mentions.all()] if c.mentions.exists() else []
                }
                for c in recent
            ]
        })
    
    # ========== MENTIONS ==========
    
    @action(detail=True, methods=['get'])
    def mentions(self, request, pk=None):
        ticket = self.get_object()
        mentions = Conversation.objects.filter(
            ticket=ticket,
            is_internal_note=True,
            mentions__isnull=False
        ).order_by('-created_at')
        
        result = []
        for conv in mentions:
            result.append({
                'conversation_id': conv.id,
                'message': conv.message,
                'mentioned_by': conv.sender_name,
                'mentioned_at': conv.created_at,
                'mentioned_agents': [
                    {
                        'id': agent.id,
                        'username': agent.user.username,
                        'department': agent.department
                    }
                    for agent in conv.mentions.all()
                ]
            })
        
        return Response({
            'ticket_id': ticket.id,
            'total_mentions': mentions.count(),
            'mentions': result
        })
    
    @action(detail=False, methods=['get'])
    def mentioned_me(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=401)
        
        try:
            agent = Agent.objects.get(user=request.user)
            conversations = Conversation.objects.filter(
                mentions=agent,
                is_internal_note=True
            ).select_related('ticket').order_by('-created_at')
            
            tickets = []
            for conv in conversations:
                tickets.append({
                    'ticket_id': conv.ticket.id,
                    'ticket_title': conv.ticket.title,
                    'mentioned_by': conv.sender_name,
                    'mentioned_at': conv.created_at,
                    'message': conv.message,
                    'ticket_status': conv.ticket.status,
                    'ticket_priority': conv.ticket.priority
                })
            
            return Response({
                'total_mentions': conversations.count(),
                'tickets': tickets
            })
        except Agent.DoesNotExist:
            return Response({"error": "You are not registered as an agent"}, status=400)
    
    # ========== AI FEATURES ==========
    
    @action(detail=False, methods=['post'])
    def ai_analyze(self, request):
        title = request.data.get('title', '')
        description = request.data.get('description', '')
        
        if not title or not description:
            return Response({"error": "title and description required"}, status=400)
        
        analysis = classify_ticket(title, description)
        return Response(analysis)
    
    @action(detail=True, methods=['post'])
    def ai_suggest_response(self, request, pk=None):
        ticket = self.get_object()
        latest_conversation = ticket.conversations.filter(
            sender_type='customer'
        ).last()
        
        if not latest_conversation:
            return Response({"error": "No customer message found"}, status=400)
        
        suggested = generate_canned_response(
            ticket.title,
            latest_conversation.message
        )
        
        return Response({"suggested_response": suggested})
    
    @action(detail=False, methods=['get'])
    def ai_status(self, request):
        health = check_ai_health()
        return Response(health)

class ConversationViewSet(viewsets.ModelViewSet):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    
    def get_queryset(self):
        queryset = Conversation.objects.all()
        ticket_id = self.request.query_params.get('ticket', None)
        if ticket_id:
            queryset = queryset.filter(ticket_id=ticket_id)
        return queryset
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class TicketAttachmentViewSet(viewsets.ModelViewSet):
    queryset = TicketAttachment.objects.all()
    serializer_class = TicketAttachmentSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    def get_queryset(self):
        queryset = TicketAttachment.objects.all()
        ticket_id = self.request.query_params.get('ticket', None)
        if ticket_id:
            queryset = queryset.filter(ticket_id=ticket_id)
        return queryset
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def create(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        ticket_id = request.data.get('ticket')
        uploaded_by = request.data.get('uploaded_by', 'customer')
        
        if not file_obj:
            return Response({"error": "No file provided"}, status=400)
        
        if not ticket_id:
            return Response({"error": "ticket_id required"}, status=400)
        
        # Check file size
        if file_obj.size > 5 * 1024 * 1024:
            return Response({"error": "File size exceeds 5MB limit"}, status=400)
        
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            
            attachment = TicketAttachment.objects.create(
                ticket=ticket,
                file=file_obj,
                filename=file_obj.name,
                file_size=file_obj.size,
                uploaded_by=uploaded_by
            )
            
            serializer = self.get_serializer(attachment)
            return Response(serializer.data, status=201)
            
        except Ticket.DoesNotExist:
            return Response({"error": "Ticket not found"}, status=404)
    
    @action(detail=False, methods=['get'])
    def by_ticket(self, request):
        ticket_id = request.query_params.get('ticket_id')
        if not ticket_id:
            return Response({"error": "ticket_id required"}, status=400)
        
        attachments = TicketAttachment.objects.filter(ticket_id=ticket_id)
        serializer = self.get_serializer(attachments, many=True)
        return Response(serializer.data)

class CannedCategoryViewSet(viewsets.ModelViewSet):
    queryset = CannedCategory.objects.all()
    serializer_class = CannedCategorySerializer
    
    def get_queryset(self):
        queryset = CannedCategory.objects.all()
        org_id = self.request.query_params.get('organization', None)
        if org_id:
            queryset = queryset.filter(organization_id=org_id)
        return queryset
    
    @action(detail=True, methods=['get'])
    def responses(self, request, pk=None):
        category = self.get_object()
        responses = category.canned_responses.all()
        serializer = CannedResponseSerializer(responses, many=True)
        return Response(serializer.data)

class CannedResponseViewSet(viewsets.ModelViewSet):
    queryset = CannedResponse.objects.all()
    serializer_class = CannedResponseSerializer
    
    def get_queryset(self):
        queryset = CannedResponse.objects.all()
        org_id = self.request.query_params.get('organization', None)
        category_id = self.request.query_params.get('category', None)
        department = self.request.query_params.get('department', None)
        
        if org_id:
            queryset = queryset.filter(organization_id=org_id)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if department:
            queryset = queryset.filter(Q(department=department) | Q(department=''))
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def render(self, request):
        """Render a canned response with actual ticket data"""
        canned_id = request.data.get('canned_response_id')
        ticket_id = request.data.get('ticket_id')
        
        if not canned_id or not ticket_id:
            return Response({"error": "canned_response_id and ticket_id required"}, status=400)
        
        try:
            canned = CannedResponse.objects.get(id=canned_id)
            ticket = Ticket.objects.get(id=ticket_id)
            
            # Simple context with only what we know exists
            context = {
                'customer_name': ticket.customer.name,
                'customer_email': ticket.customer.email,
                'ticket_id': str(ticket.id),
                'ticket_title': ticket.title,
                'ticket_status': ticket.status,
                'ticket_priority': ticket.priority,
                'order_number': 'N/A',
                'status': ticket.status,
                'tracking_link': '#',
                'agent_name': request.user.username, 
            }
            
            # Manual replacement
            rendered = canned.content
            for key, value in context.items():
                placeholder = f'{{{{{key}}}}}'
                rendered = rendered.replace(placeholder, str(value))
            
            return Response({
                'rendered_content': rendered,
                'ticket_id': ticket.id,
                'canned_title': canned.title,
            })
            
        except CannedResponse.DoesNotExist:
            return Response({"error": "Canned response not found"}, status=404)
        except Ticket.DoesNotExist:
            return Response({"error": "Ticket not found"}, status=404)
        except Exception as e:
            print(f"Render error: {str(e)}")
            return Response({"error": str(e)}, status=500)
    
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        canned = self.get_object()
        sample_data = {
            'customer_name': 'John Doe',
            'customer_email': 'john@example.com',
            'order_number': 'ORD-12345',
            'order_status': 'shipped',
            'tracking_link': 'https://track.example.com/12345',
            'agent_name': 'Support Agent',
            'ticket_id': 123,
            'organization_name': 'QuickCart'
        }
        preview = canned.render(sample_data)
        return Response({
            'preview': preview,
            'variables': canned.variables,
            'original': canned.content
        })
    
    @action(detail=True, methods=['post'])
    def increment_usage(self, request, pk=None):
        canned = self.get_object()
        canned.usage_count += 1
        canned.save(update_fields=['usage_count'])
        return Response({'usage_count': canned.usage_count})
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        org_id = request.query_params.get('organization', 1)
        limit = int(request.query_params.get('limit', 10))
        
        popular = CannedResponse.objects.filter(
            organization_id=org_id
        ).order_by('-usage_count')[:limit]
        
        serializer = self.get_serializer(popular, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_department(self, request):
        department = request.query_params.get('department', '')
        org_id = request.query_params.get('organization', 1)
        
        if department:
            responses = CannedResponse.objects.filter(
                Q(department=department) | Q(department=''),
                organization_id=org_id
            )
        else:
            responses = CannedResponse.objects.filter(organization_id=org_id)
        
        serializer = self.get_serializer(responses, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_shortcode(self, request):
        shortcode = request.query_params.get('code', '')
        org_id = request.query_params.get('organization', 1)
        
        if not shortcode:
            return Response({"error": "code parameter required"}, status=400)
        
        try:
            response = CannedResponse.objects.get(
                shortcode=shortcode,
                organization_id=org_id
            )
            serializer = self.get_serializer(response)
            return Response(serializer.data)
        except CannedResponse.DoesNotExist:
            return Response({"error": "Canned response not found"}, status=404)

class RoutingRuleViewSet(viewsets.ModelViewSet):
    queryset = RoutingRule.objects.all()
    serializer_class = RoutingRuleSerializer
    
    def get_queryset(self):
        queryset = RoutingRule.objects.all()
        org_id = self.request.query_params.get('organization', None)
        if org_id:
            queryset = queryset.filter(organization_id=org_id, is_active=True)
        return queryset
    
class KnowledgeCategoryViewSet(viewsets.ModelViewSet):
    queryset = KnowledgeCategory.objects.all()
    serializer_class = KnowledgeCategorySerializer
    
    def get_queryset(self):
        queryset = KnowledgeCategory.objects.all()
        org_id = self.request.query_params.get('organization', None)
        if org_id:
            queryset = queryset.filter(organization_id=org_id)
        return queryset
    
    @action(detail=True, methods=['get'])
    def articles(self, request, pk=None):
        """Get all articles in this category"""
        category = self.get_object()
        articles = category.articles.filter(is_published=True)
        serializer = KnowledgeArticleSerializer(articles, many=True, context={'request': request})
        return Response(serializer.data)

class KnowledgeArticleViewSet(viewsets.ModelViewSet):
    queryset = KnowledgeArticle.objects.all()
    serializer_class = KnowledgeArticleSerializer
    
    def get_serializer_class(self):
        """Use different serializers for public vs admin"""
        if self.request.query_params.get('public', 'false').lower() == 'true':
            return PublicKnowledgeArticleSerializer
        return KnowledgeArticleSerializer
    
    def get_queryset(self):
        queryset = KnowledgeArticle.objects.all()
        org_id = self.request.query_params.get('organization', None)
        
        # Filter by organization
        if org_id:
            queryset = queryset.filter(organization_id=org_id)
        
        # Filter by category
        category_id = self.request.query_params.get('category', None)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filter by published status (for public views)
        public = self.request.query_params.get('public', 'false').lower() == 'true'
        if public:
            queryset = queryset.filter(is_published=True, is_public=True)
        
        # Search
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(content__icontains=search) | 
                Q(summary__icontains=search) | 
                Q(tags__icontains=search)
            )
        
        # Filter by tag
        tag = self.request.query_params.get('tag', None)
        if tag:
            queryset = queryset.filter(tags__icontains=tag)
        
        # Featured only
        featured = self.request.query_params.get('featured', 'false').lower() == 'true'
        if featured:
            queryset = queryset.filter(is_featured=True)
        
        return queryset
    
    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to increment view count"""
        instance = self.get_object()
        
        # Increment views
        public = request.query_params.get('public', 'false').lower() == 'true'
        if public:
            instance.increment_views()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def feedback(self, request, pk=None):
        """Submit feedback for an article"""
        article = self.get_object()
        
        is_helpful = request.data.get('is_helpful')
        if is_helpful is None:
            return Response({"error": "is_helpful required"}, status=400)
        
        # Update article counts
        if is_helpful:
            article.helpful_count += 1
        else:
            article.not_helpful_count += 1
        article.save()
        
        # Create feedback record
        feedback = ArticleFeedback.objects.create(
            article=article,
            is_helpful=is_helpful,
            comment=request.data.get('comment', ''),
            session_id=request.data.get('session_id', ''),
            customer_id=request.data.get('customer_id') if request.data.get('customer_id') else None
        )
        
        serializer = ArticleFeedbackSerializer(feedback)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get most viewed articles"""
        org_id = request.query_params.get('organization', 1)
        limit = int(request.query_params.get('limit', 10))
        
        articles = KnowledgeArticle.objects.filter(
            organization_id=org_id,
            is_published=True
        ).order_by('-views')[:limit]
        
        serializer = self.get_serializer(articles, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def helpful(self, request):
        """Get most helpful articles"""
        org_id = request.query_params.get('organization', 1)
        limit = int(request.query_params.get('limit', 10))
        
        articles = KnowledgeArticle.objects.filter(
            organization_id=org_id,
            is_published=True
        ).order_by('-helpful_count')[:limit]
        
        serializer = self.get_serializer(articles, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get most recent articles"""
        org_id = request.query_params.get('organization', 1)
        limit = int(request.query_params.get('limit', 10))
        
        articles = KnowledgeArticle.objects.filter(
            organization_id=org_id,
            is_published=True
        ).order_by('-created_at')[:limit]
        
        serializer = self.get_serializer(articles, many=True)
        return Response(serializer.data)

class ArticleFeedbackViewSet(viewsets.ModelViewSet):
    queryset = ArticleFeedback.objects.all()
    serializer_class = ArticleFeedbackSerializer
    
    def get_queryset(self):
        queryset = ArticleFeedback.objects.all()
        article_id = self.request.query_params.get('article', None)
        if article_id:
            queryset = queryset.filter(article_id=article_id)
        return queryset