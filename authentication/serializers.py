from django.contrib.auth import get_user_model, password_validation
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

User = get_user_model()


# ======================
# Register
# ======================
class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, label="Confirm Password")
    role = serializers.ChoiceField(choices=["admin", "planner", "vendor", "guest"], required=True)
    # opsional: izinkan FE tidak mengirim username
    username = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password", "password2",
            "first_name", "last_name",
            "role",
            "company",
        )

    def validate_email(self, v: str) -> str:
        v = (v or "").strip().lower()
        # pastikan unik secara case-insensitive
        if User.objects.filter(email__iexact=v).exists():
            raise serializers.ValidationError("Email sudah terdaftar.")
        return v

    def validate(self, attrs):
        # cek password match
        if attrs.get("password") != attrs.get("password2"):
            raise serializers.ValidationError({"password": "Password tidak sama."})
        password_validation.validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        role = validated_data.pop("role")
        validated_data.pop("password2", None)
        raw_password = validated_data.pop("password")

        # normalisasi company ke UPPER
        company = (validated_data.get("company") or "").strip()
        if company:
            validated_data["company"] = company.upper()

        # auto-username dari email jika kosong
        username = (validated_data.get("username") or "").strip()
        if not username:
            email_val = validated_data.get("email")
            base = email_val.split("@")[0]
            candidate = email_val  # boleh juga langsung pakai email sebagai username
            i = 1
            from django.db.models import Q
            while User.objects.filter(Q(username__iexact=candidate)).exists():
                candidate = f"{base}_{i}"
                i += 1
            validated_data["username"] = candidate

        user = User(**validated_data)
        user.set_password(raw_password)

        # set role & flags
        if role == "admin":
            user.is_staff = True
            user.is_superuser = True
            user.role = "admin"
        else:
            user.role = role

        user.is_active = True  # akun aktif saat dibuat
        user.save()
        return user


# ======================
# User detail & listing
# ======================
class UserSerializer(serializers.ModelSerializer):
    # FE kadang pakai 'name' → map ke first_name
    name = serializers.CharField(source="first_name", required=False)
    # expose status boolean dari is_active
    status = serializers.BooleanField(source="is_active", required=False)

    class Meta:
        model = User
        fields = (
            "id", "email", "username",
            "name", "first_name", "last_name",
            "role", "company", "phone", "experience", "specialty",
            "status",
        )
        read_only_fields = ("username",)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # sembunyikan field planner kalau bukan planner (opsional)
        if instance.role != "planner":
            for k in ("company", "phone", "experience", "specialty"):
                data.pop(k, None)
        return data


class UserListSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="first_name", read_only=True)
    status = serializers.BooleanField(source="is_active", read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "username", "name", "role", "status")


# ======================
# Password reset
# ======================
class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        return (value or "").strip().lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, label="Confirm Password")

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("password2"):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        password_validation.validate_password(attrs["password"])
        return attrs


# ======================
# Google OAuth request body
# ======================
class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(required=True)
    role = serializers.ChoiceField(
        choices=["admin", "planner", "vendor", "guest"],
        required=False
    )


# ======================
# (Baru) Login pakai email ATAU username
# ======================
class EmailOrUsernameLoginSerializer(serializers.Serializer):
    """
    Serializer ini memudahkan FE mengirim `email` ATAU `username`.
    Gunakan di view login untuk resolve `username`:
      - jika `email` diisi → cari user & set `username` untuk SimpleJWT
      - jika `username` diisi → pakai apa adanya
    """
    email = serializers.EmailField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = (attrs.get("email") or "").strip().lower()
        username = (attrs.get("username") or "").strip()
        password = attrs.get("password")

        if not email and not username:
            raise serializers.ValidationError("Provide either 'email' or 'username'.")

        resolved_username = username
        if email and not username:
            try:
                u = User.objects.get(email__iexact=email)
                resolved_username = u.username
            except User.DoesNotExist:
                # biar konsisten errornya di SimpleJWT (invalid credentials),
                # kita tetap teruskan username yang tidak ada.
                resolved_username = email  # fallback, tidak masalah

        return {
            "username": resolved_username,
            "password": password,
        }