from django.urls import reverse

import pytest


@pytest.mark.django_db
def test_profile_email_change_triggers_task(client, user, mocker):
    """Проверка успешной смены пароля"""
    client.force_login(user)

    old_email = user.email
    new_email = "new@mail.com"
    assert old_email != new_email

    task = mocker.patch("users.views.users_views.send_confirm_email_task.delay")

    response = client.post(
        reverse("users:profile"),
        {
            "form_type": "profile",
            "email": new_email,
            "username": user.username,
            "timezone": user.timezone,  # ← важно!
        },
        follow=True,
    )

    user.refresh_from_db()

    assert response.status_code == 200
    assert task.call_count == 1
    assert user.email == new_email or user.email_new == new_email
