from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from accounts.services import AuthService
from .serializers import (
    LoginSerializer,
    LogoutSerializer,
    RefreshSerializer,
    RegisterSerializer,
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
)


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="user_logout",
        request=LogoutSerializer,
        responses={
            200: OpenApiResponse(description="Logged out successfully, refresh token blacklisted"),
            400: OpenApiResponse(description="Invalid refresh token"),
        },
        tags=["Authentication"],
        summary="Logout & Blacklist Token",
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()

        return Response({"success": True, "message": "Logged out successfully."})


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="get_authenticated_user_me",
        responses={200: OpenApiResponse(description="Basic authenticated identity and role")},
        tags=["Authentication"],
        summary="Current User Identity",
    )
    def get(self, request):
        return Response(
            {
                "id": str(request.user.id),
                "name": request.user.full_name,
                "email": request.user.email,
                "role": request.user.role,
            }
        )


class RefreshAPIView(APIView):
    permission_classes = []

    @extend_schema(
        operation_id="refresh_jwt_token",
        request=RefreshSerializer,
        responses={200: OpenApiResponse(description="New JWT access token")},
        tags=["Authentication"],
        summary="Refresh Access Token",
    )
    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh = RefreshToken(serializer.validated_data["refresh"])
        return Response({"access": str(refresh.access_token)}, status=status.HTTP_200_OK)


class LoginAPIView(APIView):
    permission_classes = []

    @extend_schema(
        operation_id="jwt_login",
        request=LoginSerializer,
        responses={200: LoginSerializer},
        tags=["Authentication"],
        summary="JWT Login",
        description="Authenticate a user by email and password and return JWT access and refresh tokens.",
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class RegisterAPIView(APIView):
    permission_classes = []

    @extend_schema(
        operation_id="register_user",
        request=RegisterSerializer,
        responses={201: OpenApiResponse(description="User registered with JWT tokens and profile data")},
        tags=["Authentication"],
        summary="Register New User",
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = AuthService.register_user(serializer.validated_data)
        tokens = AuthService.generate_tokens(user)
        return Response(
            {
                "success": True,
                "message": "Registration successful.",
                **tokens,
                "user": {
                    "id": str(user.id),
                    "full_name": user.full_name,
                    "email": user.email,
                    "role": user.role,
                }
            },
            status=status.HTTP_201_CREATED,
        )


class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="change_password",
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password changed successfully"),
            400: OpenApiResponse(description="Current password incorrect or validation error"),
        },
        tags=["Authentication"],
        summary="Change Password",
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        success = AuthService.change_password(
            request.user,
            serializer.validated_data["current_password"],
            serializer.validated_data["new_password"],
        )
        if not success:
            return Response(
                {"success": False, "message": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"success": True, "message": "Password changed successfully."})


class ForgotPasswordAPIView(APIView):
    permission_classes = []

    @extend_schema(
        operation_id="forgot_password_request",
        request=ForgotPasswordSerializer,
        responses={200: OpenApiResponse(description="Password reset email queued")},
        tags=["Authentication"],
        summary="Forgot Password",
        description="Sends a password reset email if the account exists.",
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.send_password_reset_email(
            request,
            serializer.validated_data["email"],
        )
        return Response(
            {"success": True, "message": "If an account exists with this email, a password reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class ResetPasswordAPIView(APIView):
    permission_classes = []

    @extend_schema(
        operation_id="reset_password_confirm",
        request=ResetPasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password reset successful"),
            400: OpenApiResponse(description="Invalid or expired reset token"),
        },
        tags=["Authentication"],
        summary="Reset Password Confirm",
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        success = AuthService.reset_password(
            serializer.validated_data["uid"],
            serializer.validated_data["token"],
            serializer.validated_data["new_password"],
        )

        if not success:
            return Response(
                {"success": False, "message": "Invalid or expired password reset token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"success": True, "message": "Password reset successful. You can now login with your new password."}
        )