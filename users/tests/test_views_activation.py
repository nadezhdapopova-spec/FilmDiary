import pytest
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import authenticate


@pytest.mark.django_db
def test_activate_user_success(client, inactive_user):
    """Успешная активация профиля пользователя"""
    token = default_token_generator.make_token(inactive_user)
    url = reverse("users:activate", args=[inactive_user.pk, token])

    response = client.get(url)
    inactive_user.refresh_from_db()

    assert inactive_user.is_active is True
    assert response.status_code == 302


@pytest.mark.django_db
def test_activate_blocked_user(client, blocked_user):
    """Активация заблокированного пользователя"""
    token = default_token_generator.make_token(blocked_user)
    url = reverse("users:activate", args=[blocked_user.pk, token])

    response = client.get(url)

    assert response.url == reverse("users:activation_error")


@pytest.mark.django_db
def test_resend_activation_rate_limit(client, inactive_user):
    """Повторная отправка письма для активации"""
    client.session[f"last_resend_{inactive_user.pk}"] = timezone.now().timestamp()
    client.session.save()

    response = client.post(reverse("users:resend_activation"), {
        "email": inactive_user.email
    })

    assert response.status_code == 302


@pytest.mark.django_db
def test_auth_backend_allows_inactive_user(inactive_user):
    """Login с is_active=False"""
    user = authenticate(
        username=inactive_user.email,
        password="password123"
    )

    assert user is not None
