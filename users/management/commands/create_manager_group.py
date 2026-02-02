from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Создает группу Manager, если она не создана"

    def handle(self, *args, **options):
        User = get_user_model()
        group, created = Group.objects.get_or_create(name="Manager")

        user_ct = ContentType.objects.get_for_model(User)  # Permissions для User
        perms = Permission.objects.filter(content_type=user_ct)
        group.permissions.set(perms)  # все права на User

        group.permissions.add(
            Permission.objects.get(codename="view_user_films"),
            Permission.objects.get(codename="view_user_reviews"),
            Permission.objects.get(codename="view_user_calendar"),
        )

        self.stdout.write(f"Группа Manager {"создана" if created else "обновлена"}")
