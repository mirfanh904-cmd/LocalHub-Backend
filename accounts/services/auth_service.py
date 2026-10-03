from accounts.models import User
from django.contrib.auth import authenticate, login, logout
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode


class AuthService:

    @staticmethod
    def register_user(data):
        user = User.objects.create_user(
            email=data["email"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            phone=data["phone"],
            password=data["password"],
        )

        return user

    @staticmethod
    def login_user(request, data):
        email = data["email"]
        password = data["password"]
        user = authenticate(request, email=email, password=password)
        if user is None:
            return None
        login(request, user)
        if not data.get("remember_me"):
            request.session.set_expiry(0)

        return user

    @staticmethod
    def logout_user(request):
        logout(request)

    @staticmethod
    def generate_tokens(user):
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

    @staticmethod
    def change_password(user, current_password, new_password):
        if not user.check_password(current_password):
            return False
        user.set_password(new_password)
        user.save()
        return True

    @staticmethod
    def send_password_reset_email(request, email):

        form = PasswordResetForm(
            {
                "email": email,
            }
        )

        if form.is_valid():
            form.save(
                request=request,
                use_https=request.is_secure(),
            )

        return True

    @staticmethod
    def reset_password(uid, token, new_password):

        try:

            user_id = urlsafe_base64_decode(uid).decode()

            user = User.objects.get(
                pk=user_id,
            )

        except Exception:

            return False

        if not default_token_generator.check_token(
                user,
                token,
        ):
            return False

        user.set_password(
            new_password,
        )

        user.save()

        return True