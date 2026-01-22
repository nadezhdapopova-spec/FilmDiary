from collections import defaultdict
from zoneinfo import ZoneInfo
from datetime import time

from celery import shared_task
from django.utils import timezone
from django.db import transaction
import requests

from calendar_events.models import CalendarEvent
from config.settings import TELEGRAM_URL, TELEGRAM_TOKEN

@shared_task
def send_telegram_message(chat_id: int, message: str):
    """Отправляет сообщение в Телеграм"""
    params = {
        "text": message,
        "chat_id": chat_id,
    }
    url = f"{TELEGRAM_URL}{TELEGRAM_TOKEN}/sendMessage"

    try:
        response = requests.post(url, params=params, timeout=5)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Telegram error: {e}")


@shared_task
def send_daily_reminders():
    """
    Проверяет, что у пользователя сейчас 12:00–12:09 по местному времени и отправляет
    напоминание о запланированном на текущий день просмотре фильма.
    Напоминание отправляется один раз
    """
    now_utc = timezone.now()
    events = (CalendarEvent.objects.filter(
        user__tg_chat_id__isnull=False,
        status="planned",
        reminder_sent=False
    ).select_related("user", "film"))

    events_by_user = defaultdict(list)

    for event in events:
        user_tz = ZoneInfo(event.user.timezone)
        user_now = now_utc.astimezone(user_tz)

        if (
                event.planned_date == user_now.date()
                and time(12, 0) <= user_now.time() < time(12, 10)
        ):
            events_by_user[event.user].append(event)

    for user, user_events in events_by_user.items():
        film_list = "\n".join(
            f"• {event.film.title}" for event in user_events
        )

        message = f"🎬 Сегодня запланированы просмотры:\n{film_list}"
        with transaction.atomic():  # защищает от частично выполненных действий
            send_telegram_message.delay(user.tg_chat_id, message)
            CalendarEvent.objects.filter(id__in=[event.id for event in user_events]).update(reminder_sent=True)
