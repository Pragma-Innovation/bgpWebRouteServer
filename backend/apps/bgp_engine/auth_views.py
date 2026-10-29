"""
Authentication views and custom JWT serializers for bgpWebRouteServer.
Embeds normalized RBAC roles into JWT payload and user profile responses.
"""
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from .permissions import get_user_role


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT serializer that injects the user's operational role and metadata
    into both the JWT claims and the authentication response body.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['role'] = get_user_role(user)
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        role = get_user_role(self.user)
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email or '',
            'role': role,
            'is_staff': self.user.is_staff,
            'is_superuser': self.user.is_superuser,
            'groups': list(self.user.groups.values_list('name', flat=True)),
        }
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    """API endpoint to obtain JWT access + refresh tokens with user profile."""
    serializer_class = CustomTokenObtainPairSerializer


class CurrentUserView(APIView):
    """API endpoint to fetch the currently authenticated user's profile and RBAC role."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        role = get_user_role(user)
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email or '',
            'role': role,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'groups': list(user.groups.values_list('name', flat=True)),
        })
