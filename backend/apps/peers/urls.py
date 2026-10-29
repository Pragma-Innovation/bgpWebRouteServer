from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BgpPeerConfigViewSet

router = DefaultRouter()
router.register(r'configs', BgpPeerConfigViewSet, basename='peer-configs')
router.register(r'peers', BgpPeerConfigViewSet, basename='peers')

urlpatterns = [
    path('', include(router.urls)),
]
