from django.contrib import admin

from calendar_events.models import CalendarEvent


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    """Добавляет сообщения обратной связи пользователей в админ-панель"""

    list_display = ("id", "user", "film", "planned_date", "note", "created_at")
    search_fields = ("id", "planned_date", "created_at")
