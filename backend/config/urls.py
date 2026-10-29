from django.contrib import admin
from django.urls import path, include
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.db import connection
from rest_framework_simplejwt.views import TokenRefreshView
from apps.bgp_engine.manager import BgpManager
from apps.bgp_engine.auth_views import CustomTokenObtainPairView, CurrentUserView


@api_view(['GET'])
@permission_classes([AllowAny])
def health_live(request):
    """Kubernetes liveness probe: returns 200 if web server is responsive."""
    return Response({'status': 'ok', 'service': 'bgpWebRouteServer'})


@api_view(['GET'])
@permission_classes([AllowAny])
def health_ready(request):
    """Kubernetes readiness probe: verifies database and BGP backend connectivity."""
    db_ok = True
    try:
        connection.ensure_connection()
    except Exception as e:
        db_ok = False
        db_error = str(e)

    bgp_backend = BgpManager.get_active_backend()
    status_info = bgp_backend.get_server_status()

    is_ready = db_ok and status_info.get('ready', True)
    response_status = 200 if is_ready else 503

    return Response({
        'status': 'ready' if is_ready else 'degraded',
        'database': 'ok' if db_ok else f'error: {db_error}',
        'bgp_backend': status_info,
    }, status=response_status)


urlpatterns = [
    path('admin/', admin.site.urls),

    # Health probes for Kubernetes and monitoring
    path('api/health/live/', health_live, name='health-live'),
    path('api/health/ready/', health_ready, name='health-ready'),

    # API v1 routes
    path('api/v1/flowspec/', include('apps.flowspec.urls')),
    path('api/v1/peers/', include('apps.peers.urls')),
    path('api/v1/bgp/', include('apps.bgp_engine.urls')),
    path('api/v1/prefixes/', include('apps.prefixes.urls')),
    path('api/v1/routing/', include('apps.routing.urls')),

    # Authentication & Profile routes (JWT)
    path('api/v1/auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/auth/user/', CurrentUserView.as_view(), name='current_user'),
]
