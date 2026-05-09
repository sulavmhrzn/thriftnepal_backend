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


# TODO: For phase 2
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
