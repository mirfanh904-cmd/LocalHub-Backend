from django.urls import path
from .views import (LogoutAPIView, MeAPIView, LoginAPIView,
                    RefreshAPIView, RegisterAPIView, ChangePasswordAPIView,
                    ForgotPasswordAPIView, ResetPasswordAPIView)

urlpatterns = [

    path("login/",LoginAPIView.as_view(),name="jwt_login",),

    path("refresh/",RefreshAPIView.as_view(),name="jwt_refresh",),

    path("logout/",LogoutAPIView.as_view(),name="jwt_logout",),

    path("me/",MeAPIView.as_view(), name="jwt_me",),
    path("register/", RegisterAPIView.as_view(), name="jwt_register"),
    path("change-password/", ChangePasswordAPIView.as_view(), name="api_change_password"),
    path("forget-password/", ForgotPasswordAPIView.as_view(), name="api-forget-password"),
    path("reset-password/", ResetPasswordAPIView.as_view(), name="api_reset_password"),

]