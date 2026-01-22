from django.urls import include, path

from rest_framework.routers import DefaultRouter

from calendar_events.views import CalendarEventViewSet


router = DefaultRouter()
router.register(r"calendar_events", CalendarEventViewSet, basename="calendar_events")

urlpatterns = [
    path("", include(router.urls)),
]
