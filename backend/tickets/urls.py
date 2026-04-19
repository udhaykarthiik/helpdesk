from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'organizations', views.OrganizationViewSet)
router.register(r'customers', views.CustomerViewSet)
router.register(r'agents', views.AgentViewSet)
router.register(r'tickets', views.TicketViewSet)
router.register(r'conversations', views.ConversationViewSet)
router.register(r'attachments', views.TicketAttachmentViewSet)
router.register(r'canned-categories', views.CannedCategoryViewSet)
router.register(r'canned-responses', views.CannedResponseViewSet)
router.register(r'routing-rules', views.RoutingRuleViewSet)

router.register(r'knowledge-categories', views.KnowledgeCategoryViewSet)
router.register(r'knowledge-articles', views.KnowledgeArticleViewSet)
router.register(r'article-feedback', views.ArticleFeedbackViewSet)

urlpatterns = [
    path('', include(router.urls)),
]