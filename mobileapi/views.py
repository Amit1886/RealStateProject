from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

@api_view(['GET'])
def app_home(request):
    return Response({
        "app": "JaisTech KhataBook",
        "status": "Live",
        "version": "1.0",
        "message": "Welcome to JaisTech Professional Mobile App"
    })



@api_view(['POST'])
def login_api(request):
    user = authenticate(
        username=request.data.get('username'),
        password=request.data.get('password')
    )

    if user:
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })

    return Response({'error': 'Invalid credentials'}, status=401)