import pytest
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.contrib.auth.models import Group

from services.permissions import (
    is_manager,
    can_user_edit,
    can_user_delete,
    can_user_view,
)


@pytest.mark.django_db
def test_is_manager_true(user):
    """Возвращает True, если пользователь состоит в группе Manager"""
    group = Group.objects.create(name="Manager")
    user.groups.add(group)

    assert is_manager(user) is True


@pytest.mark.django_db
def test_is_manager_false(user):
    """Возвращает False, если пользователь не состоит в группе Manager"""
    assert is_manager(user) is False

@pytest.mark.django_db
def test_can_user_edit_owner(user, review):
    """Владелец объекта может редактировать его"""
    can_user_edit(user, review)  # не должно быть исключения


@pytest.mark.django_db
def test_can_user_edit_superuser(admin_user, review):
    """Суперпользователь может редактировать любой объект"""
    can_user_edit(admin_user, review)


@pytest.mark.django_db
def test_can_user_edit_forbidden(other_user, review):
    """Посторонний пользователь не может редактировать объект"""
    with pytest.raises(PermissionDenied):
        can_user_edit(other_user, review)

@pytest.mark.django_db
def test_can_user_delete_owner(user, review):
    """Владелец объекта может удалить его"""
    can_user_delete(user, review)


@pytest.mark.django_db
def test_can_user_delete_forbidden(other_user, review):
    """Посторонний пользователь не может удалить объект"""
    with pytest.raises(PermissionDenied):
        can_user_delete(other_user, review)

@pytest.mark.django_db
def test_can_user_view_owner(user, review):
    """Владелец объекта может просматривать карточку"""
    assert can_user_view(user, review) is True


@pytest.mark.django_db
def test_can_user_view_manager(manager_user, review):
    """Менеджер может просматривать карточки других пользователей"""
    assert can_user_view(manager_user, review) is True


@pytest.mark.django_db
def test_can_user_view_superuser(admin_user, review):
    """Суперпользователь может просматривать любые карточки"""
    assert can_user_view(admin_user, review) is True


@pytest.mark.django_db
def test_can_user_view_unauthenticated(anon_user, review):
    """Неавторизованный пользователь получает 404"""
    with pytest.raises(Http404):
        can_user_view(anon_user, review)


@pytest.mark.django_db
def test_can_user_view_forbidden(other_user, review):
    """Посторонний авторизованный пользователь получает 404"""
    with pytest.raises(Http404):
        can_user_view(other_user, review)
