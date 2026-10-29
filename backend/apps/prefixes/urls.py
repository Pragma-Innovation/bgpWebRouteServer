from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IpPrefixViewSet

router = DefaultRouter()
router.register(r'', IpPrefixViewSet, basename='prefix')

urlpatterns = [
    path('', include(router.urls)),
]
