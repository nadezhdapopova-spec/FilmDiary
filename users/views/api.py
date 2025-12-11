from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny
from .serializers import RegisterSerializer, CustomUserSerializer
from users.models import CustomUser

class RegisterAPIView(CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


class CustomUserViewSet(ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
