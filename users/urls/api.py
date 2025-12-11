from django.urls import path
from rest_framework.permissions import AllowAny
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from users.views.api import RegisterAPIView, CustomUserViewSet


app_name = "users_api"
router = DefaultRouter()
router.register("users", CustomUserViewSet, basename="users")

urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("token/", TokenObtainPairView.as_view(permission_classes=[AllowAny]), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(permission_classes=[AllowAny]), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
]

urlpatterns += router.urls
