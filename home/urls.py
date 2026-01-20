from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.welcome_message, name='welcome'),
    path("login", views.LoginAPIView.as_view(), name="login"),
    path("logout", views.LogoutAPIView.as_view(), name="logout"),
    path("signup", views.SignupAPIView.as_view(), name="signup"),
    path(
        "change-password", views.ChangePasswordAPIView.as_view(), name="change-password"
    ),
    path("profile", views.UserProfileDetails.as_view(), name="profile"),
    path("update-profile", views.UpdateProfileAPIView.as_view(), name="update-profile"),
    path("verify-email/", views.VerifyEmailAPIView.as_view(), name="verify-email"),
    path("reset-password", views.ResetPasswordAPIView.as_view(), name="reset-password"),
    # path("request-otp", views.RequestOTPView.as_view(), name="request-otp"),
    path("request-email-otp", views.RequestEmailOTPView.as_view(), name="request-email-otp"),
    path("confirm-otp", views.ConfirmOTPView.as_view(), name="confirm-otp"),
    # JWT Token endpoints
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
# 322520, 288126, 586445