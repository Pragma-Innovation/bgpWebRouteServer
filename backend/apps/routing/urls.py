from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PseudoRibViewSet, BgpCommunityViewSet, BgpAnnouncementViewSet, RibViewSet

router = DefaultRouter()
router.register(r'ribs', RibViewSet, basename='rib')
router.register(r'pseudo-ribs', PseudoRibViewSet, basename='pseudo-rib')
router.register(r'communities', BgpCommunityViewSet, basename='community')
router.register(r'announcements', BgpAnnouncementViewSet, basename='announcement')

urlpatterns = [
    path('', include(router.urls)),
]
