from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from django.db import IntegrityError
import os


class Command(BaseCommand):
    help = "Создает суперпользователя Admin, если он не создан"

    def handle(self, *args, **options):
        user = get_user_model()
        try:
            if not user.objects.filter(email=os.getenv("SUPERUSER_EMAIL")).exists():
                user.objects.create_superuser(
                    email=os.getenv("SUPERUSER_EMAIL"),
                    password=os.getenv("SUPERUSER_PASSWORD"),
                    username="Admin",
                )
                self.stdout.write(self.style.SUCCESS("Суперпользователь Admin успешно создан"))
            else:
                self.stdout.write(self.style.WARNING("Суперпользователь Admin уже существует"))
        except IntegrityError as e:
            self.stdout.write(self.style.ERROR(f"Ошибка создания суперпользователя Admin: {e}"))
