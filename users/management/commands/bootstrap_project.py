from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Полная инициализация проекта: группа → менеджер → суперпользователь"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Запуск bootstrap..."))

        try:
            self.stdout.write("Создание/обновление группы Manager")
            call_command("create_manager_group")

            self.stdout.write("Создание менеджера")
            call_command("create_manager")

            self.stdout.write("Создание суперпользователя")
            call_command("create_superuser")

            self.stdout.write(self.style.SUCCESS("Bootstrap завершен успешно"))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Ошибка bootstrap: {e}"))
