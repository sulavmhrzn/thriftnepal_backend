from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import YAMLPermission
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
        return Response(
            {
                "message": "User registered successfully",
                "data": serializer.data,
            }
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.GET)
        serializer.is_valid(raise_exception=True)
        user = verify_email(serializer.validated_data["token"])
        return Response(
            {
                "message": "User email verified successfully",
                "data": {"email": user.email},
            }
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = login_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        out = TokenResponseSerializer(tokens)

        return Response(
            {
                "message": "Tokens created successfully",
                "data": out.data,
            }
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        logout_user(serializer.validated_data["refresh"])
        return Response({"message": "Logged out successfully"})


class UserListView(APIView):
    resource_name = "users"
    permission_classes = [YAMLPermission]

    def get(self, request):
        users = list_all_users(request.GET)
        serializer = UserListSerializer(users, many=True)
        return Response(
            {"message": "Users fetched successfully.", "data": serializer.data}
        )
