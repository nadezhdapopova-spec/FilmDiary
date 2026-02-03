from datetime import date, timedelta

import pytest

from calendar_events.models import CalendarEvent


@pytest.mark.django_db
def test_calendar_owner_only(api_client, user, film, django_user_model):
    """Пользователь не может видеть события другого"""
    other = django_user_model.objects.create_user(email="other@test.com", username="other", password="pass123")
    event = CalendarEvent.objects.create(user=other, film=film, planned_date=date.today() + timedelta(days=1))
    api_client.force_authenticate(user)
    response = api_client.get(f"/api/calendar_events/{event.id}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_manager_can_view_foreign_event(api_client, manager, future_event):
    """Проверка: manager видит всё"""
    api_client.force_authenticate(manager)
    response = api_client.get(f"/api/calendar_events/{future_event.id}/")

    assert response.status_code == 200
