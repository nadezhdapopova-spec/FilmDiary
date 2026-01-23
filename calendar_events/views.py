from datetime import timedelta

from django.utils import timezone
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from calendar_events.models import CalendarEvent
from calendar_events.paginators import CalendarEventPaginator
from calendar_events.serializers import CalendarEventSerializer


class CalendarEventViewSet(viewsets.ModelViewSet):
    """Вьюсет запланированных к просмотру фильмов пользователя"""

    serializer_class = CalendarEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ["planned_date", "film"]
    ordering = ["-planned_date"]
    pagination_class = CalendarEventPaginator

    def get_queryset(self):
        """Возвращает фильмы пользователя, запланированные к просмотру"""
        return CalendarEvent.objects.filter(user=self.request.user).select_related("film")

    def perform_create(self, serializer):
        """При создании запланированного события устанавливает пользователя как владельца"""
        serializer.save(user=self.request.user)


    @action(detail=False, methods=["get"])
    def upcoming(self, request):
        """Возвращает фильмы пользователя, запланированные на ближайшие 48 часов"""
        now = timezone.now().date()
        events = self.get_queryset().filter(
            planned_date__gte=now,
            planned_date__lte=now + timedelta(days=2),  # ближайшие 48 часов
            status=CalendarEvent.Status.PLANNED
        )
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)
