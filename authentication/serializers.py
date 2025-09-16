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
    # role boleh salah satu: admin/planner/vendor/guest
    role = serializers.ChoiceField(choices=["admin", "planner", "vendor", "guest"])

    class Meta:
        model = User
        fields = ("username", "email", "password", "password2",
                  "first_name", "last_name", "role")

    def validate_email(self, v): return v.strip().lower()

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

        # admin == superuser
        if role == "admin":
            user.is_staff = True
            user.is_superuser = True
            user.role = "admin"
        else:
            user.role = role

        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='first_name', required=False)

    class Meta:
        model = User
        fields = ("id", "email", "name", "role", "company", "phone", "experience", "specialty")
        extra_kwargs = {
            'password': {'write_only': True},
            'company': {'required': False, 'allow_blank': True},
            'phone': {'required': False, 'allow_blank': True},
            'experience': {'required': False, 'allow_blank': True},
            'specialty': {'required': False, 'allow_blank': True},
        }

    def validate(self, attrs):
        role = attrs.get('role')

        # For planner role, validate that required planner fields might be provided
        # But don't make them strictly required since frontend handles this
        if role == 'planner':
            # Optional validation - you can add specific rules here if needed
            pass
        elif role == 'vendor':
            # Clear planner-specific fields for vendors
            attrs.pop('company', None)
            attrs.pop('phone', None)
            attrs.pop('experience', None)
            attrs.pop('specialty', None)

        return attrs

    def to_representation(self, instance):
        # Convert Django User to frontend format
        data = super().to_representation(instance)

        # Don't expose planner fields for non-planner users
        if instance.role != 'planner':
            data.pop('company', None)
            data.pop('phone', None)
            data.pop('experience', None)
            data.pop('specialty', None)

        return data


class UserListSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='first_name', read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "name", "role")
        read_only_fields = fields


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

        # Validate password strength
        password_validation.validate_password(attrs["password"])
        return attrs


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(required=True)
    role = serializers.ChoiceField(
        choices=["Admin", "Planner", "Vendor", "Guest"],
        required=False
    )
