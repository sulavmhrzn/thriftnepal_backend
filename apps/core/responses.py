from rest_framework import status
from rest_framework.response import Response


def success_response(
    message: str,
    data=None,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    return Response(
        {
            "success": True,
            "message": message,
            "data": data,
        },
        status=status_code,
    )


def paginated_response(
    message: str,
    data,
    pagination: dict,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    return Response(
        {
            "success": True,
            "message": message,
            "data": data,
            "pagination": pagination,
        },
        status=status_code,
    )


def get_paginated_data(paginator, queryset, request, serializer_class) -> dict:
    page = paginator.paginate_queryset(queryset, request)

    if page is not None:
        serializer = serializer_class(page, many=True)
        return {
            "message": None,
            "data": serializer.data,
            "pagination": {
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "page_size": paginator.page_size,
            },
        }

    serializer = serializer_class(queryset, many=True)
    return {
        "message": None,
        "data": serializer.data,
        "pagination": {
            "next": None,
            "previous": None,
            "page_size": None,
        },
    }
