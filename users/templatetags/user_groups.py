from django import template

register = template.Library()

@register.filter
def has_group(user, group_name):
    """Относится ли пользователь к группе пользователей"""
    if not user.is_authenticated:
        return False
    return user.groups.filter(name=group_name).exists()
