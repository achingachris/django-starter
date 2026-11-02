from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from .serializers import CustomUserSerializer


@extend_schema(responses=CustomUserSerializer)
@api_view(["GET"])
def me(request: Request) -> Response:
    """Return the logged-in user. Authenticates with a session cookie or an allauth X-Session-Token."""
    return Response(CustomUserSerializer(request.user).data)
