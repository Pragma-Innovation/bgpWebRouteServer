from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FlowspecRuleViewSet

router = DefaultRouter()
router.register(r'rules', FlowspecRuleViewSet, basename='flowspec-rules')

urlpatterns = [
    path('', include(router.urls)),
]
