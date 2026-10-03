from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.forms import RegisterForm
from accounts.services import AuthService
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()

    password = serializers.CharField(
        write_only=True,
    )

    def validate(self, attrs):
        email = attrs.get("email")

        password = attrs.get("password")

        user = authenticate(
            username=email,
            password=password,
        )

        if not user:
            raise serializers.ValidationError(
                "Invalid email or password."
            )

        tokens = AuthService.generate_tokens(user)

        return {
            **tokens,
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role,
            }
        }


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=15)
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        form = RegisterForm(
            data={
                "first_name": attrs["first_name"],
                "last_name": attrs.get("last_name", ""),
                "email": attrs["email"],
                "phone": attrs["phone"],
                "password": attrs["password"],
                "confirm_password": attrs["confirm_password"],
            }
        )

        if not form.is_valid():
            raise serializers.ValidationError(form.errors)

        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, )
    new_password = serializers.CharField(write_only=True, )
    confirm_password = serializers.CharField(write_only=True, )

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {
                    "confirm_password": "Passwords do not match."
                })
        try:
            validate_password(attrs["new_password"])
        except DjangoValidationError as e:
            raise serializers.ValidationError(
                {
                    "new_password": e.messages
                })
        return attrs

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True,)
    confirm_password = serializers.CharField(
        write_only=True,)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {
                    "confirm_password": "Passwords do not match."
                })
        try:
            validate_password(
                attrs["new_password"],)
        except DjangoValidationError as e:
            raise serializers.ValidationError(
                {
                    "new_password": e.messages,
                })
        return attrs