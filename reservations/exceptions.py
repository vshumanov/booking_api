import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("reservations")


class OverlapConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The requested dates overlap an existing booking or block on this property."
    default_code = "overlap_conflict"


def structured_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)

    if response is None:
        # Unhandled exception -> 500. Log the traceback, return a clean body.
        logger.error("Unhandled exception", exc_info=exc)
        from rest_framework.response import Response

        return Response(
            {"error": "internal_server_error", "details": "An unexpected error occurred."},
            status=500,
        )

    response.data = {
        "error": _label_for_status(response.status_code),
        "details": response.data,
    }
    return response


def _label_for_status(status_code: int) -> str:
    return {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
    }.get(status_code, "error")
