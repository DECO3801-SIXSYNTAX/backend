# authentication/views.py
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.models import Group
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str

from django.db.models import Q

from rest_framework import status, viewsets, permissions
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from authentication.permissions import IsAdmin
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    UserListSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer,
    GoogleAuthSerializer,
)

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
        t["role"] = getattr(user, "role", "")
        t["company"] = getattr(user, "company", None)
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
    # returns { refresh, access, user }
    return Response(ser.validated_data, status=200)

# ===== LOGOUT =====
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def logout(request):
    # JWT is stateless → client should delete tokens itself.
    return Response({"detail": "Logged out"}, status=200)

# ===== USER CRUD (company-scoped list for admin) =====
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        # Admin can list users in their own company
        if self.action == "list":
            return [IsAuthenticated(), IsAdmin()]
        # Anyone authenticated can hit retrieve; queryset will scope it
        if self.action == "retrieve":
            return [IsAuthenticated()]
        # Keep create/update/delete authenticated (tune to your policy)
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "list":
            return UserListSerializer   # minimal fields for listing
        return UserSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        if self.action == "list":
            # Only users from the same company as the admin
            admin_company = (getattr(self.request.user, "company", "") or "").strip().upper()

            roles_param = self.request.query_params.get("role")
            roles = [r.strip() for r in roles_param.split(",")] if roles_param else ["admin", "planner"]

            qs = qs.filter(company__iexact=admin_company, role__in=roles).order_by(
                "first_name", "last_name", "email"
            )

            q = self.request.query_params.get("q")
            if q:
                qs = qs.filter(
                    Q(first_name__icontains=q)
                    | Q(last_name__icontains=q)
                    | Q(email__icontains=q)
                    | Q(username__icontains=q)
                )

        if self.action == "retrieve":
            # Non-admin can only retrieve themselves
            if getattr(self.request.user, "role", "") != "admin":
                return qs.filter(id=self.request.user.id)
            # Admin can retrieve users in their company only
            admin_company = (getattr(self.request.user, "company", "") or "").strip().upper()
            return qs.filter(company__iexact=admin_company)

        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        password = request.data.get("password")
        user_data = serializer.validated_data

        # Map 'name' → 'first_name' if FE sends it as name
        if "first_name" in user_data:
            user_data["first_name"] = user_data.pop("first_name")

        # Auto username from email if missing
        if "email" in user_data and "username" not in user_data:
            email = user_data["email"]
            username = email
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{email.split('@')[0]}_{counter}"
                counter += 1
            user_data["username"] = username

        user = User(**user_data)
        if password:
            user.set_password(password)
        user.save()

        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        password = request.data.get("password")
        if password:
            instance.set_password(password)

        self.perform_update(serializer)
        return Response(UserSerializer(instance).data)

# ===== PASSWORD RESET (uniform response) =====
token_generator = PasswordResetTokenGenerator()

@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset(request):
    """
    Always returns the same message (enumeration-safe).
    """
    serializer = PasswordResetSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data["email"]

    try:
        user = User.objects.get(email=email)
        token = token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_link = f"http://localhost:3000/reset-password/{uid}/{token}"

        subject = "Password Reset Request"
        message = f"""
Hello {user.first_name or user.username},

You have requested a password reset for your account.

Click the link below to reset your password:
{reset_link}

If you did not request this password reset, please ignore this email.

Best regards,
SiPanit Team
"""
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@sipanit.com"),
            recipient_list=[email],
            fail_silently=True,
        )
    except User.DoesNotExist:
        # Do not reveal existence
        pass

    return Response(
        {"detail": "If this email is registered, you will receive a password reset link shortly."},
        status=status.HTTP_200_OK,
    )

@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    serializer = PasswordResetConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    uid = serializer.validated_data["uid"]
    token = serializer.validated_data["token"]
    password = serializer.validated_data["password"]

    try:
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"error": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)

        if not token_generator.check_token(user, token):
            return Response({"error": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(password)
        user.save()

        return Response({"detail": "Password has been reset successfully."}, status=status.HTTP_200_OK)
    except Exception:
        return Response({"error": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)

# ===== GOOGLE OAUTH =====
class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        id_token_str = serializer.validated_data["id_token"]
        role_name = serializer.validated_data.get("role", "Guest")

        try:
            idinfo = google_id_token.verify_oauth2_token(
                id_token_str,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except ValueError:
            return Response({"detail": "Invalid Google ID token."}, status=status.HTTP_400_BAD_REQUEST)

        if not idinfo.get("email_verified", False):
            return Response({"detail": "Google email is not verified."}, status=status.HTTP_400_BAD_REQUEST)

        email = idinfo["email"]
        full_name = idinfo.get("name", "") or ""
        first = full_name.split(" ")[0] if full_name else ""
        last = " ".join(full_name.split(" ")[1:]) if " " in full_name else ""

        user, created = User.objects.get_or_create(
            email=email,
            defaults={"username": email, "first_name": first, "last_name": last},
        )

        if created and role_name:
            group, _ = Group.objects.get_or_create(name=role_name)
            user.groups.add(group)

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