import os
import sys
from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env", override=True)

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS").split(",")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "drf_yasg",
    "django_celery_beat",
    "corsheaders",
    "rest_framework_simplejwt",
    "crispy_forms",
    "crispy_bootstrap5",
    "users",
    "films",
    "reviews",
    "calendar_events",
]

CRISPY_ALLOWED_TEMPLATE_PACKS = ["bootstrap5"]
CRISPY_TEMPLATE_PACK = "bootstrap5"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "middleware.BlockUserMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": "127.0.0.1",
        "PORT": os.getenv("DB_PORT"),
        "CONN_MAX_AGE": 0,       # закрываем после КАЖДОГО запроса, каждое соединение свежее
        "OPTIONS": {
            'connect_timeout': 5,  # таймаут подключения, Django ждет подключения к PostgreSQL 5 секунд, а не 30
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 5,
            "keepalives_count": 3,
        },
    }
}

if "test" in sys.argv:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "test_bd.sqlite3",
        }
    }

# Default primary key field type

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization

LANGUAGE_CODE = "ru"

TIME_ZONE = "Europe/Moscow"

USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# MESSAGE_TAGS

from django.contrib.messages import constants as messages

MESSAGE_TAGS = {
    messages.DEBUG: "secondary",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "danger",
}

# Users settings

AUTHENTICATION_BACKENDS = [
    "users.backends.EmailBackendAllowInactive",  # к кастомному backend
    "django.contrib.auth.backends.ModelBackend",  # для админки, базовый бэкенд аутентификации, проверяет базу данных пользователей Django и запрашивает встроенные разрешения
]

AUTH_USER_MODEL = "users.CustomUser"
LOGIN_REDIRECT_URL = "users:profile"
LOGOUT_REDIRECT_URL = "users:login"
LOGIN_URL = "users:login"

# Настройки срока действия токенов

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
}

# Caches settings

CACHE_ENABLED = True
if CACHE_ENABLED:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": os.getenv("LOCATION"),
        }
    }

# Rest_framework settings

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 12,
}

SWAGGER_USE_COMPAT_RENDERERS = False

# CORS

CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
]

# CELERY

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")
CELERY_TIMEZONE = "Europe/Moscow"
CELERY_ENABLE_UTC = False
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

CELERY_BEAT_SCHEDULE = {
    "send_daily_calendar_reminders": {
        "task": "calendar_events.tasks.send_daily_reminders",
        "schedule": crontab(hour=13, minute=0),
        # "schedule": crontab(minute="*/1"),   # каждую минуту
    },
    "recompute-recommendations-nightly": {
        "task": "films.tasks.recompute_all_recommendations",
        "schedule": crontab(hour=13, minute=0),
        # "schedule": crontab(minute="*/1"),
    }
}


# Mail server settings

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = os.getenv("EMAIL_PORT")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "False").lower() == "true"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False").lower() == "true"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
SERVER_EMAIL = EMAIL_HOST_USER
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# TELEGRAM INTEGRATION

TELEGRAM_URL = "https://api.telegram.org/bot"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


# recommendations.py
# Вес признаков
RECOMMENDER_FEATURE_WEIGHTS = {
    "director": 3.0,
    "actor": 2.0,
    "genre": 1.5,
    "keyword": 1.0,
}

# Весовое соотношение content / text
RECOMMENDER_WEIGHT_STRUCT = 0.7
RECOMMENDER_WEIGHT_TEXT = 0.3

# Максимальный порог количества фич в TF-IDF
RECOMMENDER_TFIDF_MAX_FEATURES = 5000

# Отбор кандидатов: рекомендуемое оптимальное количество
RECOMMENDER_TOP_K_BASE = 200

# Параметры нормализации рейтинга
RECOMMENDER_RATING_MIN = 1
RECOMMENDER_RATING_MAX = 10

# Параметры весов жанров профиля
RECOMMENDER_GENRE_BOOST_STRATEGY = "max"
RECOMMENDER_GENRE_PROFILE_WEIGHT = 0.25
RECOMMENDER_GENRE_SIMILARITY_WEIGHT = 0.2

# Параметры весов жанров API
RECOMMENDER_API_GENRE_PRIOR_WEIGHT = 0.1
RECOMMENDER_API_SIMILAR_WEIGHT = 0.15
RECOMMENDER_API_RECOMMENDED_WEIGHT = 0.2

# Окончательное масштабирование: параметры мягкости, чтобы избежать полного обнуления
RECOMMENDER_RATING_SOFTNESS = 0.5
RECOMMENDER_RECENCY_SOFTNESS = 0.5


# logging settings

BASE_DIR = Path(__file__).resolve().parent.parent

LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO")
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_HANDLERS = {
    "console": {
        "class": "logging.StreamHandler",
        "formatter": "simple",
        "level": LOG_LEVEL,
    },
    "file_app": {
        "class": "logging.handlers.RotatingFileHandler",
        "formatter": "verbose",
        "level": LOG_LEVEL,
        "filename": LOG_DIR / "app.log",
        "maxBytes": 5 * 1024 * 1024,
        "backupCount": 3,
        "encoding": "utf-8",
    },
}

MODULE_HANDLERS = {
    "films": LOG_DIR / "films.log",
    "reviews": LOG_DIR / "reviews.log",
    "events": LOG_DIR / "events.log",
    "telegram": LOG_DIR / "telegram.log",
    "users": LOG_DIR / "users.log",
}

for name, filename in MODULE_HANDLERS.items():
    LOG_HANDLERS[f"file_{name}"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "formatter": "verbose",
        "level": LOG_LEVEL,
        "filename": filename,
        "maxBytes": 5 * 1024 * 1024,
        "backupCount": 3,
        "encoding": "utf-8",
    }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "verbose": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(pathname)s:%(lineno)d | %(message)s",
        },
        "simple": {
            "format": "%(levelname)s | %(name)s | %(message)s",
        },
        "celery": {
            "format": "%(asctime)s | %(levelname)s | [%(name)s:%(task_id)s] | %(message)s",
        },
    },

    "handlers": LOG_HANDLERS,

    "root": {
        "handlers": ["console", "file_app"],
        "level": LOG_LEVEL,
    },

    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": True,
        },
        "django.request": {          # 404/500 ошибки
            "handlers": ["file_app"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.db.backends": {
            "level": "ERROR",        # SQL только ошибки
        },

        "filmdiary.films": {"handlers": ["file_films"], "level": LOG_LEVEL, "propagate": False},
        "filmdiary.reviews": {"handlers": ["file_reviews"], "level": LOG_LEVEL, "propagate": False},
        "filmdiary.events": {"handlers": ["file_events"], "level": LOG_LEVEL, "propagate": False},
        "filmdiary.telegram": {"handlers": ["file_telegram"], "level": LOG_LEVEL, "propagate": False},
        "filmdiary.users": {"handlers": ["file_users"], "level": LOG_LEVEL, "propagate": False},

        "films.tasks": {"handlers": ["console", "file_app"], "level": "INFO", "propagate": False},
        "users.tasks": {"handlers": ["console", "file_app"], "level": "INFO", "propagate": False},
    },
}
