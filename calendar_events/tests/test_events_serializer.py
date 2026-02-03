from datetime import date, timedelta

import pytest


@pytest.mark.django_db
def test_calendar_serializer_prevents_duplicates(api_client, user, film):
    """Нельзя запланировать один фильм на одну дату дважды"""
    api_client.force_authenticate(user)
    payload = {
        "film": film.id,
        "planned_date": date.today() + timedelta(days=1),
    }
    api_client.post("/api/calendar_events/", payload)
    response = api_client.post("/api/calendar_events/", payload)

    assert response.status_code == 400
    assert "Этот фильм уже запланирован" in str(response.data)
