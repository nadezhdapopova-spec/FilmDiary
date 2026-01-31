import logging
from datetime import timedelta

from django.utils import timezone
from django.utils.timezone import now
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from calendar_events.models import CalendarEvent
from calendar_events.paginators import CalendarEventPaginator
from calendar_events.permissions import ManagerOrOwnerPermission
from calendar_events.serializers import CalendarEventSerializer



class CalendarEventViewSet(viewsets.ModelViewSet):
    """Вьюсет запланированных к просмотру фильмов пользователя"""
    serializer_class = CalendarEventSerializer
    permission_classes = [ManagerOrOwnerPermission]
    filter_backends = [OrderingFilter]
    ordering_fields = ["planned_date", "film"]
    ordering = ["planned_date"]
    pagination_class = CalendarEventPaginator
    logger = logging.getLogger("filmdiary.events")

    def get_queryset(self):
        """Возвращает фильмы пользователя, запланированные к просмотру"""
        qs = CalendarEvent.objects.filter(user=self.request.user).select_related("film")

        view = self.request.query_params.get("view", "active")
        today = now().date()

        if view == "archive":
            qs = qs.filter(planned_date__lt=today)
        else:
            qs = qs.filter(planned_date__gte=today)

        return qs.order_by("planned_date")

    def perform_create(self, serializer):
        """При создании запланированного события устанавливает пользователя как владельца"""
        serializer.save(user=self.request.user)
        self.logger.info("Calendar CREATE: user=%s event=%s film=%s",
                         self.request.user.id, serializer.instance.pk,
                         serializer.instance.film.tmdb_id)


    @action(detail=False, methods=["get"])
    def upcoming(self, request):
        """Возвращает фильмы пользователя, запланированные на ближайшие 48 часов"""
        self.logger.debug("Calendar upcoming: user=%s", request.user.id)
        now = timezone.now().date()
        events = self.get_queryset().filter(
            planned_date__gte=now,
            planned_date__lte=now + timedelta(days=2),  # ближайшие 48 часов
        )
        self.logger.info("Calendar upcoming: user=%s count=%s",
                         request.user.id, events.count())
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)
