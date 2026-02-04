from datetime import datetime, timezone

import pytest

from calendar_events.models import CalendarEvent
from calendar_events.tasks import send_daily_reminders


@pytest.mark.django_db
def test_send_daily_reminders_sends_and_marks(mocker, user, film):
    """Напоминание отправляется и помечается reminder_sent=True"""
    user.tg_chat_id = 123456
    user.timezone = "Europe/Moscow"
    user.save()

    fake_now_utc = datetime(2026, 2, 3, 9, 10, tzinfo=timezone.utc)
    mocker.patch("django.utils.timezone.now", return_value=fake_now_utc)
    mocker.patch("calendar_events.tasks.timezone.now", return_value=fake_now_utc)
    planned_date = fake_now_utc.date()
    event = CalendarEvent.objects.create(
        user=user,
        film=film,
        planned_date=planned_date,
        reminder_sent=False,
    )
    mock_send = mocker.patch("calendar_events.tasks.send_telegram_message.delay")
    send_daily_reminders()
    event.refresh_from_db()

    assert event.reminder_sent is True
    mock_send.assert_called_once()
