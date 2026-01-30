import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
def test_register_creates_inactive_user(client):
    """Валидная регистрация пользователя"""
    response = client.post(
        reverse("users:register"),
        {
            "email": "new@test.com",
            "username": "newuser",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
            "timezone": "Europe/Moscow",
        },
        follow=True,
    )

    assert User.objects.count() == 1

    user = User.objects.get(email="new@test.com")
    assert user.is_active is False
    assert response.status_code == 200


@pytest.mark.django_db
def test_register_calls_send_email(mocker, client):
    """Регистрация: проверка Celery"""
    task = mocker.patch(
        "users.views.users_views.send_activation_email_task.delay"
    )

    response = client.post(
        reverse("users:register"),
        {
            "email": "new@test.com",
            "username": "newuser",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
            "timezone": "Europe/Moscow",
        },
        follow=True,
    )

    assert response.status_code == 200
    task.assert_called_once()
