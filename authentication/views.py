from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication

from .serializers import RegisterSerializer, UserSerializer, UserListSerializer

from django.conf import settings
from django.contrib.auth.models import User, Group
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework_simplejwt.tokens import RefreshToken

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from .serializers import GoogleAuthSerializer, UserSerializer

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

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


# ===== USER CRUD OPERATIONS =====
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        """
        Allow public access to list and create for frontend integration.
        Require authentication for update/delete operations.
        """
        if self.action in ['list', 'create', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        return UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Handle password if provided
        password = request.data.get('password')
        user_data = serializer.validated_data

        # Map 'name' to 'first_name' if provided
        if 'first_name' in user_data:
            name = user_data.pop('first_name')  # This comes from the 'name' field mapping
            user_data['first_name'] = name

        # Generate username from email if not provided
        if 'email' in user_data and 'username' not in user_data:
            email = user_data['email']
            # Use email as username, or email prefix if email already exists as username
            username = email
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{email.split('@')[0]}_{counter}"
                counter += 1
            user_data['username'] = username

        user = User(**user_data)
        if password:
            user.set_password(password)
        user.save()

        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # Handle password if provided
        password = request.data.get('password')
        if password:
            instance.set_password(password)

        # Save other fields
        self.perform_update(serializer)

        return Response(UserSerializer(instance).data)

class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # 1) Validate request body
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        id_token_str = serializer.validated_data["id_token"]
        role_name = serializer.validated_data.get("role", "Guest")

        # 2) Verify Google ID token (signature, issuer, and audience)
        try:
            idinfo = google_id_token.verify_oauth2_token(
                id_token_str,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,  # will fail automatically if audience does not match
            )
        except ValueError:
            return Response(
                {"detail": "Invalid Google ID token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3) Ensure the email is verified
        if not idinfo.get("email_verified", False):
            return Response(
                {"detail": "Google email is not verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 4) Get or create user
        email = idinfo["email"]
        full_name = idinfo.get("name", "") or ""
        first = full_name.split(" ")[0] if full_name else ""
        last = " ".join(full_name.split(" ")[1:]) if " " in full_name else ""

        user, created = User.objects.get_or_create(
            email=email,
            defaults={"username": email, "first_name": first, "last_name": last},
        )

        # 5) Assign role if the user is new
        if created and role_name:
            group, _ = Group.objects.get_or_create(name=role_name)
            user.groups.add(group)

        # 6) Issue JWT tokens
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": UserSerializer(user).data,
                "is_new_user": created,
                "login_provider": "google",
            },
            status=status.HTTP_200_OK,
        )