import logging

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework_simplejwt.exceptions import InvalidToken

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):

    exc = _map_django_exception(exc)

    response = exception_handler(exc, context)

    if response is not None:
        return _build_response(exc, response.data, response.status_code)

    return _handle_unhandled_exception(exc, context)


def _map_django_exception(exc):
    """Maps Django core exceptions to DRF equivalents"""
    if isinstance(exc, ObjectDoesNotExist):
        return NotFound(str(exc) or "Resource not found.")
    if isinstance(exc, DjangoPermissionDenied):
        return PermissionDenied(str(exc) or "Permission denied.")
    if isinstance(exc, DjangoValidationError):
        return ValidationError(
            detail=exc.message_dict if hasattr("exc", "message_dict") else exc.message
        )
    return exc


def _build_response(exc, detail, status_code: int) -> Response:
    """
    Builds consistent error response shape.
    """
    code = _get_code(exc)
    message = _get_message(exc)

    if status_code >= 500:
        logger.error(
            "Server error",
            extra={"code": code, "detail": detail},
            exc_info=True,
        )
    else:
        logger.warning(
            "Client error",
            extra={"code": code, "status_code": status_code},
        )

    return Response(
        {
            "error": True,
            "code": code,
            "message": message,
            "detail": detail,
        },
        status=status_code,
    )


def _handle_unhandled_exception(exc, context) -> Response:
    """
    Catches everything DRF did not handle.
    """
    logger.error(
        "Unhandled exception",
        exc_info=True,
        extra={
            "view": context.get("view").__class__.__name__
            if context.get("view")
            else None,
            "args": context.get("args"),
            "kwargs": context.get("kwargs"),
        },
    )

    return Response(
        {
            "error": True,
            "code": "server_error",
            "message": "Something went wrong. Please try again.",
            "detail": None,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _get_code(exc) -> str:
    if isinstance(exc, ValidationError):
        return "validation_error"
    if isinstance(exc, NotFound):
        return "not_found"
    if isinstance(exc, PermissionDenied):
        return "permission_denied"
    if isinstance(exc, NotAuthenticated):
        return "not_authenticated"
    if isinstance(exc, MethodNotAllowed):
        return "method_not_allowed"
    if isinstance(exc, Throttled):
        return "throttled"
    if isinstance(exc, APIException):
        return exc.default_code
    return "server_error"


def _get_message(exc) -> str:
    if isinstance(exc, ValidationError):
        return "Validation error."
    if isinstance(exc, NotFound):
        return "Resource not found."
    if isinstance(exc, PermissionDenied):
        return "Permission denied."
    if isinstance(exc, NotAuthenticated):
        return "Authentication required."
    if isinstance(exc, MethodNotAllowed):
        return "Method not allowed."
    if isinstance(exc, Throttled):
        return "Too many requests. Slow down."
    if isinstance(exc, InvalidToken):
        return "Token is invalid"
    if isinstance(exc, APIException):
        return str(exc.detail)

    return "Something went wrong."
