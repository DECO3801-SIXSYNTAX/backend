from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.models import Group
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str

from django.db.models import Q

from rest_framework import status, viewsets, permissions
from rest_framework.decorators import (
    api_view, permission_classes, authentication_classes, action
)
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied

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
    EmailOrUsernameLoginSerializer,   # <- bridge email/username
)

User = get_user_model()

# ======================
# Register / Login / Logout
# ======================

@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    ser = RegisterSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    user = ser.save()
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class _LoginSerializer(TokenObtainPairSerializer):
    """Extend JWT serializer to inject custom claims + return user in response."""
    @classmethod
    def get_token(cls, user):
        t = super().get_token(user)
        t["username"] = user.username
        t["role"] = getattr(user, "role", "")
        t["company"] = getattr(user, "company", None)
        return t


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    """
    Body bisa:
      { "email": "...", "password": "..." }  ATAU  { "username": "...", "password": "..." }
    Bridge akan resolve email -> username untuk SimpleJWT.
    """
    # 1) Normalisasi kredensial (email/username) dengan bridge
    bridge = EmailOrUsernameLoginSerializer(data=request.data)
    bridge.is_valid(raise_exception=True)
    creds = bridge.validated_data   # -> { "username": "...", "password": "..." }

    # 2) Minta token ke SimpleJWT
    jwt_ser = _LoginSerializer(data=creds, context={"request": request})
    jwt_ser.is_valid(raise_exception=True)

    # 3) Sertakan data user di response
    try:
        user = User.objects.get(username=creds["username"])
        data = dict(jwt_ser.validated_data)
        data["user"] = UserSerializer(user).data
        return Response(data, status=200)
    except User.DoesNotExist:
        # Seharusnya tidak terjadi jika kredensial valid, tapi fallback aman
        return Response({"detail": "No active account found with the given credentials"}, status=401)


@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def logout(request):
    # Jika pakai stateless JWT, "logout" cukup di FE buang token;
    # endpoint ini disediakan agar FE punya satu flow konsisten.
    return Response({"detail": "Logged out"}, status=200)


# ======================
# Users (company-scoped & status actions)
# ======================

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        if self.action == "list":
            return [IsAuthenticated(), IsAdmin()]
        if self.action == "retrieve":
            return [IsAuthenticated()]
        # create/update/delete → tetap require login (atur sesuai kebijakan)
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "list":
            return UserListSerializer
        return UserSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        if self.action == "list":
            admin_company = (getattr(self.request.user, "company", "") or "").strip().upper()

            roles_param = self.request.query_params.get("role")
            roles = [r.strip() for r in roles_param.split(",")] if roles_param else ["admin", "planner"]

            qs = qs.filter(company__iexact=admin_company, role__in=roles)

            # filter status (?status=active|suspended)
            status_param = (self.request.query_params.get("status") or "").lower()
            if status_param in ("active", "suspended"):
                qs = qs.filter(is_active=(status_param == "active"))

            # search (?q=...)
            q = self.request.query_params.get("q")
            if q:
                qs = qs.filter(
                    Q(first_name__icontains=q) |
                    Q(last_name__icontains=q) |
                    Q(email__icontains=q) |
                    Q(username__icontains=q)
                )

            return qs.order_by("first_name", "last_name", "email")

    def retrieve(self, request, *args, **kwargs):
        # Non-admin hanya boleh ambil dirinya sendiri
        if getattr(self.request.user, "role", "") != "admin":
            self.kwargs["pk"] = str(self.request.user.id)
        return super().retrieve(request, *args, **kwargs)

    # ---------- helpers ----------
    def _enforce_same_company(self, target_user):
        me = (self.request.user.company or "").strip().upper()
        other = (target_user.company or "").strip().upper()
        if me != other:
            raise PermissionDenied("Cross-company operation is forbidden.")

    # ---------- actions ----------
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsAdmin])
    def suspend(self, request, pk=None):
        """
        POST /api/users/{id}/suspend/
        """
        user = self.get_object()
        self._enforce_same_company(user)
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response({"detail": "User suspended", "status": "suspended"})

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsAdmin])
    def activate(self, request, pk=None):
        """
        POST /api/users/{id}/activate/
        """
        user = self.get_object()
        self._enforce_same_company(user)
        user.is_active = True
        user.save(update_fields=["is_active"])
        return Response({"detail": "User activated", "status": "active"})

    # (opsional) create & update sederhana (admin panel/API internal)
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        password = request.data.get("password")
        user_data = serializer.validated_data

        # auto-username dari email kalau kosong
        if "email" in user_data and "username" not in user_data:
            email = user_data["email"]
            username = email
            i = 1
            while User.objects.filter(username=username).exists():
                prefix = email.split("@")[0]
                username = f"{prefix}_{i}"
                i += 1
            user_data["username"] = username

        user = User(**user_data)
        if password:
            user.set_password(password)
        if user.is_active is None:
            user.is_active = True
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


# ======================
# Password reset (uniform response)
# ======================

token_generator = PasswordResetTokenGenerator()

@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset(request):
    serializer = PasswordResetSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data["email"]

    try:
        user = User.objects.get(email__iexact=email)
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
        # Always return 200 to avoid user enumeration
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


# ======================
# Google OAuth
# ======================

class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # Debug (aman di dev)
        print("\n=== Google Auth Request ===")
        print(f"Data keys: {list(request.data.keys())}")
        print(f"Has id_token: {'id_token' in request.data}")
        print(f"Role: {request.data.get('role')}")
        print("========================\n")

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
        except ValueError as e:
            print(f"!!! Google token verification failed: {e}")
            return Response({"detail": "Invalid Google ID token."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"!!! Unexpected error during token verification: {e}")
            return Response({"detail": f"Token verification error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        if not idinfo.get("email_verified", False):
            return Response({"detail": "Google email is not verified."}, status=status.HTTP_400_BAD_REQUEST)

        email = idinfo["email"]
        full_name = idinfo.get("name", "") or ""
        first = full_name.split(" ")[0] if full_name else ""
        last = " ".join(full_name.split(" ")[1:]) if " " in full_name else ""

        # Gunakan username=email supaya unik terhadap user lokal lain
        user, created = User.objects.get_or_create(
            username=email,
            defaults={"email": email, "first_name": first, "last_name": last},
        )

        if not user.is_active:
            return Response({"detail": "Account is suspended."}, status=status.HTTP_403_FORBIDDEN)

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