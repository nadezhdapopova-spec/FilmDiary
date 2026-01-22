from rest_framework import serializers

from calendar_events.models import CalendarEvent


class CalendarEventSerializer(serializers.ModelSerializer):
    """Сериализатор привычек"""
    film_title = serializers.CharField(source="film.title", read_only=True)

    class Meta:
        model = CalendarEvent
        fields = ["id", "user", "film", "film_title", "planned_date", "status", "note", "reminder_sent", "created_at"]
        read_only_fields = ("id", "user", "film_title", "created_at")
        validators = []
