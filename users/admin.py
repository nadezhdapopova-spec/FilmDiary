from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from users.models import CustomUser, MessageFeedback


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Класс для настройки панели админа (суперпользователя)"""

    model = CustomUser
    list_display = (
        "email",
        "username",
        "tg_chat_id",
        "timezone",
        "avatar_preview",
        "is_active",
        "is_staff",
        "is_superuser",
        "is_blocked",
    )
    fieldsets = UserAdmin.fieldsets + (
        (
            "Дополнительная информация",
            {"fields": ("tg_chat_id", "timezone", "avatar", "avatar_tag")},
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "password1",
                    "password2",
                    "tg_chat_id",
                    "timezone",
                    "avatar",
                ),
            },
        ),
    )

    readonly_fields = ("avatar_tag",)

    @admin.display(description="Аватар")
    def avatar_preview(self, obj):
        """Отображает миниатюру аватара в списке"""
        if obj.avatar:
            return format_html('<img src="{}" width="40" height="40" style="border-radius:50%;" />', obj.avatar.url)
        return "—"

    @admin.display(description="Текущий аватар")
    def avatar_tag(self, obj):
        """Отображает текущий аватар пользователя"""
        if obj.avatar:
            return format_html('<img src="{}" width="100" style="border-radius:10px;" />', obj.avatar.url)
        return "—"


@admin.register(MessageFeedback)
class ReviewAdmin(admin.ModelAdmin):
    """Добавляет сообщения Обратной связи в админ-панель"""

    list_display = ("id", "name", "email", "message", "created_at")
    search_fields = ("name", "email")
