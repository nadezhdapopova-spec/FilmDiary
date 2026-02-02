from zoneinfo import ZoneInfo

from django.utils import timezone

import pytest

from calendar_events.models import CalendarEvent
from calendar_events.tasks import send_daily_reminders


@pytest.mark.django_db
def test_send_daily_reminders_sends_and_marks(mocker, user, film):
    """Напоминание отправляется и помечается reminder_sent=True"""
    user.tg_chat_id = 123456
    user.timezone = "Europe/Moscow"
    user.save()
    event = CalendarEvent.objects.create(user=user, film=film, planned_date=timezone.now().date(), reminder_sent=False)
    mock_send = mocker.patch("calendar_events.tasks.send_telegram_message.delay")
    mocker.patch(
        "calendar_events.tasks.timezone.now",
        return_value=timezone.now().replace(hour=14, minute=10, tzinfo=ZoneInfo("UTC")),
    )
    send_daily_reminders()

    event.refresh_from_db()
    assert event.reminder_sent is True
    mock_send.assert_called_once()
