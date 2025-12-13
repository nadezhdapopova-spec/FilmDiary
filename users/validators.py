from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


User = get_user_model()


def validate_avatar(file):
    """Метод валидации поля формы 'аватар' на формат и размер файла"""
    valid_content_types = ["image/jpeg", "image/jpg", "image/png"]
    max_size_mb = 5 * 1024 * 1024

    if file.content_type not in valid_content_types:
        raise ValidationError("Файл должен быть в формате JPEG или PNG")

    if file.size > max_size_mb:
        raise ValidationError(f"Размер файла не должен превышать {max_size_mb} МБ")


def validate_telegram_id(tg_id: int | None):
    if tg_id is None:
        return None
    tg_id_str = str(tg_id)
    if not tg_id_str.isdigit():
        raise ValidationError("Telegram ID должен содержать только цифры")

    if not (5 <= len(tg_id_str) <= 12):
        raise ValidationError("Telegram ID должен содержать от 5 до 12 цифр")

    if User.objects.filter(tg_chat_id=tg_id).exists():
        raise ValidationError("Этот Telegram ID уже используется")

    return tg_id
