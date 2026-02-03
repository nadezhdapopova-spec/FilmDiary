from django.core.exceptions import PermissionDenied
from django.http import Http404


def is_manager(user):
    """Проверяет, является ли пользователь менеджером приложения"""
    return user.groups.filter(name="Manager").exists()


def can_user_edit(user, obj):
    """Проверяет, может ли пользователь редактировать объект"""
    if user.is_superuser or getattr(obj, "user", None) == user:
        return
    raise PermissionDenied("Вы не можете редактировать информацию других пользователей")


def can_user_delete(user, obj):
    """Проверяет, может ли пользователь удалить объект"""
    if user.is_superuser or getattr(obj, "user", None) == user:
        return
    raise PermissionDenied("Вы не можете удалить информацию других пользователей")


def can_user_view(user, obj):
    """Проверяет доступ к карточке объекта"""
    if not user.is_authenticated:
        raise Http404("Для просмотра необходимо пройти авторизацию")
    if user.is_superuser or is_manager(user) or obj.user == user:
        return True
    raise Http404("Нет доступа")
