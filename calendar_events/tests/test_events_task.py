from datetime import date

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
    planned_date = date.today()
    event = CalendarEvent.objects.create(user=user, film=film, planned_date=planned_date, reminder_sent=False)
    fake_now_utc = timezone.now().replace(year=2026, month=2, day=3, hour=9, minute=10, second=0, microsecond=0)
    mock_send = mocker.patch("calendar_events.tasks.send_telegram_message.delay")
    mocker.patch("calendar_events.tasks.timezone.now", return_value=fake_now_utc)
    send_daily_reminders()

    event.refresh_from_db()
    assert event.reminder_sent is True
    mock_send.assert_called_once()
