from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.core.permissions import YAMLPermission
from apps.core.responses import success_response
from apps.users.serializers import (
    LoginSerializer,
    LogoutSerializer,
    RegisterSerializer,
    TokenResponseSerializer,
    UserListSerializer,
    VerifyEmailSerializer,
)
from apps.users.services import (
    list_all_users,
    login_user,
    logout_user,
    register_user,
    verify_email,
)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        register_user(**serializer.validated_data)
        return success_response(
            message="User registered successfully",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.GET)
        serializer.is_valid(raise_exception=True)
        user = verify_email(serializer.validated_data["token"])
        return success_response(
            message="User email verified successfully",
            data={"email": user.email},
            status_code=status.HTTP_200_OK,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = login_user(**serializer.validated_data, request=request)
        out = TokenResponseSerializer(tokens)

        return success_response(
            message="Tokens created successfully",
            data=out.data,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        logout_user(serializer.validated_data["refresh"])
        return success_response(message="Logged out successfully")


class UserListView(APIView):
    resource_name = "users"
    permission_classes = [YAMLPermission]

    def get(self, request):
        users = list_all_users(request.GET)
        serializer = UserListSerializer(users, many=True)
        return success_response(
            message="Users fetched successfully.",
            data=serializer.data,
        )
