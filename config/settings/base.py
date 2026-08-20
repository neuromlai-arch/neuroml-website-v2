from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django_ckeditor_5",
    "easy_thumbnails",
    "django_q",
    "csp",
    # local apps
    "core",
    "taxonomy",
    "people",
    "solutions",
    "insights",
    "marketing",
    "pages",
    "careers",
    "chat",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "csp.middleware.CSPMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.RedirectMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.megamenu",
                "core.context_processors.footer_chrome",
                "core.context_processors.site_settings",
                "core.context_processors.calendly",
                "core.context_processors.lead_popup",
                "core.context_processors.newsletter_form",
                "core.context_processors.chat_enabled",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL"),
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "admin:login"

DEFAULT_FROM_EMAIL = env("DJANGO_DEFAULT_FROM_EMAIL", default="no-reply@example.com")

# Grounded chat widget (see chat app). Empty key -> widget renders nothing;
# see core.context_processors and templates/components/_chat_widget.html.
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")
CHAT_DAILY_TOKEN_BUDGET = env.int("CHAT_DAILY_TOKEN_BUDGET", default=200_000)

# django-q2: the ORM as the broker. No Redis to run for a handful of
# notification emails a day — see CLAUDE.md's "simpler than Celery" note.
Q_CLUSTER = {
    "name": "site_backend",
    "orm": "default",
    "workers": 2,
    "timeout": 60,
    "retry": 120,
    "catch_up": False,
}

# django-ckeditor-5
CUSTOMCOLOR_PALETTE = []
CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": [
            "heading", "|",
            "bold", "italic", "link", "|",
            "bulletedList", "numberedList", "blockQuote", "|",
            "codeBlock", "insertImage", "|",
            "undo", "redo",
        ],
        "image": {
            "toolbar": ["imageTextAlternative", "|", "imageStyle:alignLeft",
                        "imageStyle:alignRight", "imageStyle:alignCenter",
                        "imageStyle:side"],
        },
    },
}
CKEDITOR_5_FILE_STORAGE = "django.core.files.storage.default_storage"

# django-unfold
UNFOLD = {
    "SITE_TITLE": "Content admin",
    "SITE_HEADER": "Content admin",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
}

# django-csp. 'unsafe-inline' on script-src covers the per-page inline
# JSON-LD blocks (breadcrumbs, FAQPage, Organization, etc.); 'unsafe-eval'
# is required by Alpine.js's default build, which evaluates x-data
# expressions via `Function()` — swap to the @alpinejs/csp build to drop it.
# 'unsafe-inline' on style-src is a concession to the admin (Unfold +
# CKEditor5 both inject inline styles).
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'", "https://unpkg.com"],
        "style-src": ["'self'", "'unsafe-inline'"],
        "img-src": ["'self'", "data:", "https:"],
        "font-src": ["'self'"],
        "connect-src": ["'self'"],
        "frame-ancestors": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
    },
}
