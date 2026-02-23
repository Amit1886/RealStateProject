from django.db.utils import OperationalError, ProgrammingError
from rest_framework import status
from rest_framework.response import Response


def db_unavailable(detail: str = "Addon tables are not ready. Run migrations for this addon.") -> Response:
    return Response({"detail": detail}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


DB_EXCEPTIONS = (OperationalError, ProgrammingError)

