from django.core.exceptions import ValidationError


def validate_number_of_views(num: int | None):
    """Валидация количества просмотров"""
    if num is not None:
        if not isinstance(num, int):
            raise ValidationError("Должно быть целое число")
        if num <= 0:
            raise ValidationError("Количество просмотров должно быть положительным")
