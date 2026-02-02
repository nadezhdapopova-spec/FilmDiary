from datetime import date, timedelta

import pytest

from calendar_events.models import CalendarEvent


@pytest.mark.django_db
def test_calendar_list_active(api_client, user, future_event):
    """По умолчанию возвращаются только будущие события"""
    api_client.force_authenticate(user)
    response = api_client.get("/api/calendar_events/")

    assert response.status_code == 200
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["id"] == future_event.id


@pytest.mark.django_db
def test_calendar_create_sets_user(api_client, user, film):
    """При создании события user берётся из request"""
    api_client.force_authenticate(user)
    response = api_client.post(
        "/api/calendar_events/",
        {
            "film": film.id,
            "planned_date": date.today() + timedelta(days=2),
        },
    )

    assert response.status_code == 201
    event = CalendarEvent.objects.get()
    assert event.user == user


@pytest.mark.django_db
def test_calendar_upcoming(api_client, user, film):
    """upcoming возвращает события на ближайшие 48 часов"""
    api_client.force_authenticate(user)
    CalendarEvent.objects.create(user=user, film=film, planned_date=date.today() + timedelta(days=1))
    CalendarEvent.objects.create(user=user, film=film, planned_date=date.today() + timedelta(days=5))
    response = api_client.get("/api/calendar_events/upcoming/")

    assert response.status_code == 200
    assert len(response.data) == 1
