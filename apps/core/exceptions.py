from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        return Response(
            {
                "error": True,
                "message": _get_message(exc),
                "detail": response.data,
            },
            status=response.status_code,
        )

    return Response(
        {
            "error": True,
            "message": "Internal server error.",
            "detail": str(exc),
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _get_message(exc) -> str:
    if isinstance(exc, ValidationError):
        return "Validation error."
    if isinstance(exc, NotFound):
        return "Resource not found."
    if isinstance(exc, PermissionDenied):
        return "Permission denied."
    return "An error occurred."
