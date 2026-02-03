from django.contrib import admin

from films.models import Film, UserFilm


@admin.register(Film)
class FilmAdmin(admin.ModelAdmin):
    """Добавляет сохраненные фильмы в админ-панель"""

    list_display = ("id", "title", "tmdb_id", "release_date", "created_at")
    search_fields = ("id", "title", "tmdb_id")


@admin.register(UserFilm)
class UserFilmAdmin(admin.ModelAdmin):
    """Добавляет фильмы пользователей в админ-панель"""

    list_display = ("id", "user", "film", "is_favorite", "created_at")
    search_fields = ("id",)
