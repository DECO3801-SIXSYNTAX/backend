from django.contrib.auth import get_user_model, password_validation
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, label="Confirm Password")
    role = serializers.ChoiceField(choices=["admin", "planner", "vendor", "guest"])

    class Meta:
        model = User
        fields = ("username", "email", "password", "password2",
                  "first_name", "last_name", "role", "company")

    def validate_email(self, v):
        return v.strip().lower()

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Password tidak sama."})
        password_validation.validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        role = validated_data.pop("role")
        validated_data.pop("password2")
        raw = validated_data.pop("password")

        user = User(**validated_data)
        user.set_password(raw)

        if role == "admin":
            user.is_staff = True
            user.is_superuser = True
            user.role = "admin"
        else:
            user.role = role

        # default: akun aktif saat dibuat
        user.is_active = True
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    # FE kadang mengirim/ingin field 'name' → map ke first_name
    name = serializers.CharField(source="first_name", required=False)
    # expose status sebagai boolean, map ke is_active
    status = serializers.BooleanField(source="is_active", required=False)

    class Meta:
        model = User
        fields = (
            "id", "email", "username", "name", "first_name", "last_name",
            "role", "company", "phone", "experience", "specialty", "status"
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


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, label="Confirm Password")

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        password_validation.validate_password(attrs["password"])
        return attrs


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(required=True)
    role = serializers.ChoiceField(
        choices=["admin", "planner", "vendor", "guest"],
        required=False
    )