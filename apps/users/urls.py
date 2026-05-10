from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.views import (
    LoginView,
    LogoutView,
    RegisterView,
    UserListView,
    VerifyEmailView,
)

urlpatterns = [
    path("users/", UserListView.as_view(), name="user-list"),
    path("register/", RegisterView.as_view(), name="register-user"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("refresh/", TokenRefreshView.as_view(), name="refresh-token"),
]
