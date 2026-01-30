import pytest
from django.urls import reverse

from users.models import MessageFeedback


@pytest.mark.django_db
def test_feedback_creates_message(client):
    """Успешная отправка сообщения в 'Обратной связи'"""
    client.post(reverse("users:feedback"), {
        "name": "Ivan",
        "email": "ivan@test.com",
        "message": "Hello!"
    })

    assert MessageFeedback.objects.count() == 1
