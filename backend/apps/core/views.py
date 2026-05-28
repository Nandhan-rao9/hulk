from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import UserSerializer, PlantLookupUploadSerializer, MaterialMappingUploadSerializer


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'detail': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(request, username=username, password=password)

        if user is None:
            return Response(
                {'detail': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        login(request, user)
        serializer = UserSerializer(user)

        # Ensure CSRF token is set
        get_token(request)

        return Response({
            'user': serializer.data,
            'message': 'Login successful'
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'message': 'Logout successful'})


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class PlantLookupUploadView(APIView):
    """
    Upload plant lookup CSV to create/update mappings.

    Requires admin role.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # Check admin role
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Admin role required'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = PlantLookupUploadSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        result = serializer.save()
        response_status = status.HTTP_200_OK if result['status'] == 'success' else status.HTTP_400_BAD_REQUEST

        return Response(result, status=response_status)


class MaterialMappingUploadView(APIView):
    """
    Upload material group mapping CSV to create mappings.

    Requires admin role. Does not update existing mappings (returns error).
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # Check admin role
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Admin role required'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = MaterialMappingUploadSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        result = serializer.save()
        response_status = status.HTTP_200_OK if result['status'] == 'success' else status.HTTP_400_BAD_REQUEST

        return Response(result, status=response_status)
