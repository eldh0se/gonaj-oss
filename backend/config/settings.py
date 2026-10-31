"""Django settings for the Gonaj backend scaffold.

All deployment-sensitive values come from the environment; missing
required values fail fast naming the variable (spec edge case).
"""
import logging
import os
import time
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

_MISSING = object()


def env(name, default=_MISSING):
    value = os.environ.get(name, default)
    if value is _MISSING:
        raise ImproperlyConfigured(
            f"Missing required environment variable: {name}"
        )
    return value


SECRET_KEY = env("DJANGO_SECRET_KEY")

DEBUG = env("DJANGO_DEBUG", "1") == "1"


def build_logging_config(debug):
    """Mode-dependent logging configuration (007, FR-001-FR-003).

    Debug mode emits everything (threshold DEBUG) for diagnosis;
    production stays restrained (threshold INFO) so routine traffic
    is silent while warnings and errors still surface. Output goes
    to the captured standard streams only — retention and rotation
    belong to the deployment environment.
    """
    level = "DEBUG" if debug else "INFO"
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "redact": {"()": "apps.core.redaction.RedactionFilter"},
        },
        "formatters": {
            "triage": {
                "format": "{asctime} {levelname} {name}: {message}",
                "style": "{",
                # Literal "Z": the wall time is UTC (converter below),
                # and "%z" is avoided because it renders inconsistently
                # across platforms when the converter is gmtime.
                "datefmt": "%Y-%m-%dT%H:%M:%SZ",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "filters": ["redact"],
                "formatter": "triage",
                "level": level,
            },
        },
        "root": {"handlers": ["console"], "level": level},
    }


# Deterministic UTC timestamps so entries order across components
# regardless of the machine's local timezone (FR-004).
logging.Formatter.converter = time.gmtime

LOGGING = build_logging_config(DEBUG)

# FR-008: a failing log write MUST NOT break the request, command, or
# response being processed. This holds because the configuration uses
# only stdlib StreamHandler, whose emit() routes write failures to
# handleError (reported, never re-raised). Add no custom handler with
# a raising emit() path; backend/tests/test_logging.py locks this in.
logging.raiseExceptions = True

ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.core",
    "apps.transport",
    "apps.journey",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "gonaj"),
        "USER": env("POSTGRES_USER", "gonaj"),
        "PASSWORD": env("POSTGRES_PASSWORD", "gonaj"),
        "HOST": env("POSTGRES_HOST", "localhost"),
        "PORT": env("POSTGRES_PORT", "5432"),
    }
}

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

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Kolkata"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "apps.transport.api.errors.plain_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "transport_minute": "180/min",
        "transport_day": "5000/day",
    },
}

# Throttle counters live in the project's own database (created with
# `manage.py createcachetable`). Set to the address of a trusted
# reverse proxy to honour forwarded-for headers; left empty, only
# the direct connection address identifies a client (FR-024).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "transport_throttle_cache",
    }
}
TRANSPORT_TRUSTED_PROXY = env("TRANSPORT_TRUSTED_PROXY", "")

# Journey helper model configuration (specs/004-journey-agent, FR-019).
# The key stays server-side only: it appears in no response, log, or
# frontend bundle. Empty default keeps management commands and the test
# suite (which stubs the model client) runnable without a key; the
# provider fails fast naming the variable on first real model use.
MODEL_API_KEY = env("MODEL_API_KEY", "")
JOURNEY_MODEL = env("JOURNEY_MODEL", "muse-spark-1.3")
JOURNEY_MODEL_PROVIDER = env("JOURNEY_MODEL_PROVIDER", "meta")
TRANSCRIBE_MODEL = env("TRANSCRIBE_MODEL", "muse-voice-transcribe-1.0")
MODEL_API_BASE_URL = env("MODEL_API_BASE_URL", "https://api.meta.ai/v1")
MODEL_TIMEOUT_SECONDS = float(env("MODEL_TIMEOUT_SECONDS", "20"))
