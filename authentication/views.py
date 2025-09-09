from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication

from .serializers import RegisterSerializer, UserSerializer

User = get_user_model()

# ===== REGISTER =====
@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    ser = RegisterSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    user = ser.save()
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

# ===== LOGIN (JWT) =====
class _LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        t = super().get_token(user)
        t["username"] = user.username
        t["role"] = user.role
        return t
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data

@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    ser = _LoginSerializer(data=request.data, context={"request": request})
    ser.is_valid(raise_exception=True)
    # berisi { refresh, access, user }
    return Response(ser.validated_data, status=200)

# ===== LOGOUT (sederhana) =====
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def logout(request):
    # JWT itu stateless → frontend/klien harus hapus tokennya sendiri.
    return Response({"detail": "Logged out"}, status=200)
