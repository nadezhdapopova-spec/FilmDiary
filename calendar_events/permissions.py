from rest_framework import permissions


class ManagerOrOwnerPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        """Проверяет авторизацию пользователя"""
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Superuser/Manager видит все, обычный пользователь — только свои объекты"""
        user = request.user

        if user.is_superuser or user.groups.filter(name="Manager").exists():
            return True
        return getattr(obj, "user", obj) == user
