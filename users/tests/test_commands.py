import pytest
from django.core.management import call_command

from users.models import CustomUser


@pytest.mark.django_db
def test_create_manager_command():
    call_command("create_manager")
    assert CustomUser.objects.filter(username="Admin_middle").exists()