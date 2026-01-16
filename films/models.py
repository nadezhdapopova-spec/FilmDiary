from django.db import models

from users.models import CustomUser


class Actor(models.Model):
    """Класс модели актера"""
    tmdb_id = models.PositiveIntegerField(unique=True, verbose_name="TMDB ID")
    name = models.CharField(max_length=255, verbose_name="Имя")
    original_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Оригинальное имя")
    profile_path = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ссылка на фото")

    def __str__(self):
        return self.name


class Genre(models.Model):
    """Класс модели жанра"""
    tmdb_id = models.PositiveIntegerField(unique=True, verbose_name="TMDB ID")
    name = models.CharField(max_length=100, verbose_name="Название")

    def __str__(self):
        return self.name


class Person(models.Model):
    """Класс модели режиссера/продюссера/сценариста/композитора"""
    tmdb_id = models.PositiveIntegerField(unique=True, verbose_name="TMDB ID")
    name = models.CharField(max_length=255, verbose_name="Имя")
    original_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Оригинальное имя")
    profile_path = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name


class Film(models.Model):
    """Класс модели фильма"""
    title = models.CharField(max_length=500, verbose_name="Название")
    tmdb_id = models.PositiveIntegerField(unique=True, verbose_name="TMDB ID")
    tagline = models.CharField(max_length=255, blank=True, null=True, verbose_name="Короткое описание")
    original_title = models.CharField(max_length=500, blank=True, null=True, verbose_name="Оригинальное название")
    genres = models.ManyToManyField(to="films.Genre", related_name="films", verbose_name="Жанры")
    overview = models.TextField(verbose_name="Описание")
    poster_path = models.CharField(max_length=250, blank=True, null=True, verbose_name="Ссылка на постер")
    backdrop_path = models.CharField(max_length=255, blank=True, null=True)
    crew = models.ManyToManyField(
        Person,
        through="FilmCrew",
        related_name="films",
        blank=True
    )
    actors = models.ManyToManyField(to="films.Actor", through="FilmActor", blank=True, related_name="films", verbose_name="Актеры")
    original_country = models.CharField(max_length=100, null=True, blank=True, verbose_name="Страна")
    runtime = models.PositiveIntegerField(null=True, blank=True, verbose_name="Продолжительность")
    release_date = models.DateField(null=True, blank=True, verbose_name="Дата выхода")
    budget = models.CharField(null=True, blank=True, verbose_name="Бюджет")
    revenue = models.CharField(null=True, blank=True, verbose_name="Мировые сборы")
    production_company = models.CharField(null=True, blank=True, verbose_name="Производство")
    vote_average = models.FloatField(null=True, blank=True, verbose_name="Средняя оценка")
    vote_count = models.PositiveIntegerField(null=True, blank=True, verbose_name="Количество оценок")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")


    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "фильм"
        verbose_name_plural = "фильмы"
        ordering = [
            "title", "-release_date"
        ]


class FilmActor(models.Model):
    """Промежуточная таблица: связь с фильмом через актера и его роль (actor/character)"""
    film = models.ForeignKey(to="films.Film", on_delete=models.CASCADE)
    actor = models.ForeignKey(to="films.Actor", on_delete=models.CASCADE)

    character = models.CharField(max_length=255, blank=True, null=True, verbose_name="Роль")
    order = models.PositiveIntegerField(default=0, verbose_name="Приоритет значимости в фильме")

    class Meta:
        ordering = ["order"]


class FilmCrew(models.Model):
    """Промежуточная таблица: связь с фильмом через должность (crew)"""
    film = models.ForeignKey(to="films.Film", on_delete=models.CASCADE)
    person = models.ForeignKey(to="films.Person", on_delete=models.CASCADE)
    job = models.CharField(max_length=100)  # Director, Writer, Composer, Producer

    class Meta:
        unique_together = ("film", "person", "job")


class UserFilm(models.Model):
    user = models.ForeignKey(
        to="users.CustomUser",
        on_delete=models.CASCADE,
        related_name="user_films",
        verbose_name="Пользователь")
    film = models.ForeignKey(
        Film,
        on_delete=models.CASCADE,
        related_name="user_relations"
    )
    is_favorite = models.BooleanField(default=False, verbose_name="Любимое")
    is_planned = models.BooleanField(default=False, verbose_name="Запланировано к просмотру")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} — {self.film}"

    class Meta:
        unique_together = ("user", "film")
        indexes = [
            models.Index(fields=["user", "film"]),
        ]
