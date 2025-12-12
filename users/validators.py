from django.core.exceptions import ValidationError


def validate_avatar(file):
    """Метод валидации поля формы 'аватар' на формат и размер файла"""
    valid_content_types = ["image/jpeg", "image/jpg", "image/png"]
    max_size_mb = 5 * 1024 * 1024

    if file.content_type not in valid_content_types:
        raise ValidationError("Файл должен быть в формате JPEG или PNG")

    if file.size > max_size_mb:
        raise ValidationError(f"Размер файла не должен превышать {max_size_mb} МБ")
