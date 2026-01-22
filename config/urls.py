from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="API Documentation",
        default_version="v1",
        description="API Documentation",
    ),
    public=True,
    permission_classes=[
        permissions.AllowAny,
    ],
)

handler400 = "films.views.custom_error"
handler403 = "films.views.custom_error"
handler404 = "films.views.custom_error"
handler500 = "films.views.custom_error"

urlpatterns = [
    path("", RedirectView.as_view(url="/films/home/", permanent=False)),
    path("admin/", admin.site.urls),
    path("api-auth/", include("rest_framework.urls")),
    path("users/", include("users.urls", namespace="users")),
    path("films/", include("films.urls", namespace="films")),
    path("reviews/", include("reviews.urls", namespace="reviews")),
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
