# authentication/views.py
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.authtoken.models import Token

from .permissions import IsAdminRole
from .serializers import AssignRoleSerializer

from rest_framework.generics import ListAPIView
from .serializers import UserListSerializer
from .permissions import IsAdminRoleOrSuperuser
from django.contrib.auth import get_user_model

User = get_user_model()

class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        groups = list(request.user.groups.values_list("name", flat=True))
        return Response({
            "id": request.user.id,
            "username": request.user.username,
            "email": request.user.email,
            "roles": groups,
        }, status=200)


class AssignUserRoleView(APIView):
    """
    Admin-only: set role user menjadi salah satu dari: Admin/Planner/Vendor/Guest.
    Mekanisme: remove dulu semua role tsb → add role baru.
    """
    permission_classes = [IsAdminRole]

    def post(self, request, user_id: int):
        ser = AssignRoleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        role = ser.validated_data["role"]

        user = User.objects.filter(pk=user_id).first()
        if not user:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        allowed = ["Admin", "Planner", "Vendor", "Guest"]
        # hapus semua role dulu
        for name in allowed:
            g = Group.objects.filter(name=name).first()
            if g:
                user.groups.remove(g)
        # tambah role baru
        group, _ = Group.objects.get_or_create(name=role)
        user.groups.add(group)

        return Response({"user": user.username, "role": role}, status=200)


class LogoutView(APIView):
    """
    Logout token-based: hapus token milik user yang sedang login.
    Idempotent: kalau token tidak ada, tetap 200.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        # opsional: buatkan token baru otomatis? (biasanya tidak)
        return Response({"detail": "Logged out"}, status=200)

class ListUsersView(ListAPIView):
    """
    Admin-only: list all users.
    Support pagination bawaan DRF (PAGE_SIZE bisa di settings).
    """
    queryset = User.objects.all().order_by("id")
    serializer_class = UserListSerializer
    permission_classes = [IsAdminRoleOrSuperuser]