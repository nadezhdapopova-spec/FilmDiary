from django.contrib.auth import get_user_model

import pytest

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="user@test.com",
        password="password123",
        username="testuser",
    )


@pytest.fixture
def inactive_user(db):
    return User.objects.create_user(
        email="inactive@test.com",
        password="password123",
        username="inactive",
        is_active=False,
    )


@pytest.fixture
def blocked_user(db):
    return User.objects.create_user(
        email="blocked@test.com",
        password="password123",
        username="blocked",
        is_blocked=True,
    )


@pytest.fixture(autouse=True)
def mock_celery_tasks(mocker):
    """Автоматически мокает ВСЕ Celery .delay() вызовы в тестах"""
    mocker.patch("celery.app.task.Task.delay")
    mocker.patch("celery.app.task.Task.apply_async")
