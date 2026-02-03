from datetime import date, timedelta

from django.contrib.auth.models import Group

import pytest
from rest_framework.test import APIClient

from calendar_events.models import CalendarEvent
from films.models import Film


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        email="user@test.com", username="user", password="pass123", timezone="Europe/Moscow"
    )


@pytest.fixture
def manager(user, django_user_model):
    group, _ = Group.objects.get_or_create(name="Manager")
    user.groups.add(group)
    return user


@pytest.fixture
def film():
    return Film.objects.create(title="Test Film", tmdb_id=123)


@pytest.fixture
def future_event(user, film):
    return CalendarEvent.objects.create(user=user, film=film, planned_date=date.today() + timedelta(days=1))


@pytest.fixture
def past_event(user, film):
    event = CalendarEvent.objects.create(user=user, film=film, planned_date=date.today() + timedelta(days=1))
    CalendarEvent.objects.filter(pk=event.pk).update(planned_date=date.today() - timedelta(days=1))
    event.refresh_from_db()
    return event
