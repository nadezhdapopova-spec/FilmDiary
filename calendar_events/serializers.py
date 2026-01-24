from rest_framework import serializers

from calendar_events.models import CalendarEvent


class CalendarEventSerializer(serializers.ModelSerializer):
    """Сериализатор привычек"""
    film_title = serializers.CharField(source="film.title", read_only=True)

    class Meta:
        model = CalendarEvent
        fields = ["id", "user", "film", "film_title", "planned_date", "note", "reminder_sent", "created_at"]
        read_only_fields = ("id", "user", "film_title", "created_at")

    def validate(self, attrs):
        """Проверяет, что указанный фильм еще не запланирован пользователем на выбранную дату"""
        user = self.context["request"].user
        film = attrs.get("film")
        planned_date = attrs.get("planned_date")

        exists = CalendarEvent.objects.filter(
            user=user,
            film=film,
            planned_date=planned_date,
        ).exists()

        if exists:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        "Этот фильм уже запланирован на выбранную дату"
                    ]
                }
            )

        return attrs
