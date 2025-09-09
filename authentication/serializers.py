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
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "role")
