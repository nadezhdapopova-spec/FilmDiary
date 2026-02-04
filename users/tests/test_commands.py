import os

from django.core.management import call_command

import pytest

from users.models import CustomUser


@pytest.mark.django_db
def test_create_manager_command(mocker):
    """Тестирует кастомную команду для создания группы Менеджер"""
    mocker.patch.dict(
        os.environ,
        {
            "MANAGER_EMAIL": "manager@test.com",
            "MANAGER_PASSWORD": "testpass123",
        },
    )

    call_command("create_manager")

    manager = CustomUser.objects.get(username="Admin_middle")
    assert manager.email == "manager@test.com"
    assert manager.is_staff
    assert manager.groups.filter(name="Manager").exists()
