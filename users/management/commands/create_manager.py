import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import IntegrityError


class Command(BaseCommand):
    help = "Создает менеджера приложения, если он не создан"

    def handle(self, *args, **options):
        User = get_user_model()

        manager_email = os.getenv("MANAGER_EMAIL")
        if not manager_email:
            self.stdout.write(self.style.ERROR("MANAGER_EMAIL не задан в .env"))
            return

        try:
            manager_user = User.objects.filter(email=manager_email).first()
            if not manager_user:
                manager_user = User.objects.create_user(
                    email=os.getenv("MANAGER_EMAIL"),
                    password=os.getenv("MANAGER_PASSWORD", "admin123"),
                    username="Admin_middle",
                    is_staff=True,
                )
                self.stdout.write(self.style.SUCCESS("Менеджер Admin_middle успешно создан"))
            else:
                self.stdout.write(self.style.WARNING("Менеджер Admin_middle уже существует"))

            group, _ = Group.objects.get_or_create(name="Manager")
            manager_user.groups.add(group)
            self.stdout.write(f"Менеджер {manager_user.username} в группе Manager")

        except IntegrityError as e:
            self.stdout.write(self.style.ERROR(f"Ошибка создания: {e}"))
        except Exception as ext:
            self.stderr.write(self.style.ERROR(f"Неожиданная ошибка: {ext}"))
