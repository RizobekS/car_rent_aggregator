import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", 'True').lower() in ['true', 'yes', '1']

# Разрешаем локальные обращения по IP
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS").split(",")
CSRF_TRUSTED_ORIGINS = os.environ.get("CSRF_TRUSTED_ORIGINS").split(",")

# CORS для dev (если будешь тестить из браузера/внешних клиентов)
CORS_ALLOW_ALL_ORIGINS = os.environ.get("CORS_ALLOW_ORIGINS", "True").lower() in ['true', 'yes', '1']


# Application definition

INSTALLED_APPS = [
    "jazzmin",
    "dal",
    "dal_select2",
    "modeltranslation",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    "paytechuz.integrations.django",
    "rest_framework",
    "django_filters",
    "corsheaders",

    # local apps
    "apps.partners",
    "apps.users",
    "apps.cars",
    "apps.bookings",
    "apps.payments",
    "apps.audit",
    "apps.common",
    "apps.dashboard",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",

    # 1) до CSRF, до Authentication
    "apps.common.middleware.ApiGatewayMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "apps.audit.middleware.RequestAuditMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE"),
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST"),
        "PORT": os.environ.get("DB_PORT"),
        "CONN_MAX_AGE": 600,
        "OPTIONS": {"connect_timeout": 5},
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

API_PREFIX = "/api/"
WEBHOOK_WHITELIST_PATHS = [
    "/api/payments/payme/webhook/",
    "/api/payments/click/webhook/",
    "/api/payments/p/",
]
BOTS_API_KEY = os.environ.get("BOTS_API_KEY")
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
}
BOT_PAY_RETURN_URL = os.environ.get("BOT_PAY_RETURN_URL", "https://t.me/")
PAYTECHUZ = {
    "PAYME": {
        "PAYME_ID":        os.environ.get("PAYME_ID"),
        "PAYME_KEY":       os.environ.get("PAYME_KEY_PROD"),

        "ACCOUNT_MODEL":   "apps.payments.models.Payment",
        "ACCOUNT_FIELD":   "id",
        "AMOUNT_FIELD":    "amount",
        "ONE_TIME_PAYMENT": True,
        "IS_TEST_MODE":    False,
    },
    "CLICK": {
        "SERVICE_ID":       os.environ.get("CLICK_SERVICE_ID"),
        "MERCHANT_ID":      os.environ.get("CLICK_MERCHANT_ID"),
        "MERCHANT_USER_ID": os.environ.get("CLICK_MERCHANT_USER_ID"),
        "SECRET_KEY":       os.environ.get("CLICK_SECRET_KEY"),
        "BASE_URL":         os.getenv("CLICK_BASE_URL", "https://my.click.uz"),

        "ACCOUNT_MODEL":    "apps.payments.models.Payment",
        "ACCOUNT_FIELD":    "id",
        "COMMISSION_PERCENT": float(os.environ.get("CLICK_COMMISSION", "0")),
        "IS_TEST_MODE":     False,
    },
}


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "ru"
LANGUAGES = [("uz", "Oʻzbekcha"), ("ru", "Русский"), ("en", "English")]
LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


MEDIA_URL = '/media/'
MEDIA_ROOT = os.getenv("MEDIA_ROOT", str(BASE_DIR / "media"))

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ───────────────────────── Jazzmin ─────────────────────────
JAZZMIN_SETTINGS = {
    # Брендинг
    "site_title": "RentCar Admin",
    "site_header": "Агрегатор автопроката",
    "site_brand": "Car Hub",
    "welcome_sign": "Добро пожаловать в панель управления",
    "copyright": "© Aggregator RentCar, 2025",
    "site_logo": "jazzmin/logo/site_logo.png",            # помести файл в STATIC/jazzmin/logo.svg
    "login_logo": "jazzmin/logo/aggregator_logo.png",          # STATIC/jazzmin/login.svg
    "login_logo_dark": "jazzmin/logo/aggregator_logo.png",
    "site_logo_classes": "img-fluid",
    "show_ui_builder": False,

    # Поиск по моделям
    "search_model": ["bookings.Booking", "cars.Car",],

    # Пользовательское меню (правый верхний угол)
    "usermenu_links": [
        #{"name": "Документация", "url": "https://docs.djangoproject.com/", "new_window": True},
        {"model": "auth.user"},
    ],

    # Верхнее меню
    "topmenu_links": [
        {"name": "Главная", "url": "admin:index"},
        # Быстрые фильтры (ссылки на ченджлисты с GET-фильтрами)
        {"name": "Автопарк", "url": "admin:cars_car_changelist"},
        {
            "name": "📊 Дашборд",
            "url": "dashboard-report",
        },
    ],

    # Левое меню: порядок и иконки
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",

        "bookings": "fas fa-clipboard-list",
        "bookings.Booking": "fas fa-calendar-check",
        "bookings.BookingExtension": "fas fa-history",

        "cars.Car": "fas fa-car-side",
        "cars.MarkCar": "fas fa-warehouse",
        "cars.ModelCar": "fas fa-car",
        "cars.ColorCar": "fas fa-palette",
        "cars.CarCalendar": "fas fa-calendar-day",
        "cars.CarImages": "fas fa-image",
        "cars.Region": "fas fa-map",

        "partners": "fas fa-handshake",
        "partners.Partner": "fas fa-building",
        "partners.PartnerUser": "fas fa-user-tie",
        "partners.PartnerAdminLink": "fas fa-link",

        "users": "fas fa-user-circle",
        "users.BotUser": "fas fa-id-card",

        "payments.Payment": "fas fa-credit-card",
        "audit.AuditEvent": "fas fa-clipboard-check",
        "common": "fas fa-cog",

        "dashboard": "fas fa-chart-line",
    },
    "custom_links": {
        "audit": [{
                "name": "Обзор и аналитика",
                "url": "dashboard-report",   # name в urls.py
                "icon": "fas fa-chart-bar",

        }]
    },

    # Секции в левом меню (необязательно; если не задавать — Jazzmin сам разложит)
    "order_with_respect_to": [
        "dashboard", "partners", "cars", "bookings", "payments", "users", "audit", "auth",
    ],

    # Поведение форм
    "related_modal_active": False,         # внешние ключи открывать во всплывающем модальном окне
    "changeform_format": "tabs",          # формы редактирования разбивать на вкладки
    "changeform_format_overrides": {
        "bookings.Booking": "collapsible",  # пример: у Booking сделаем «аккордеоны»
    },

    # Языковой переключатель (полезно с modeltranslation)
    "language_chooser": True,
}

# Небольшой тюнинг темы
JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": True,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-primary",
    "navbar": "navbar-success navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": False,
    "sidebar": "sidebar-dark-success",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": True,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-outline-primary",
        "secondary": "btn-outline-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    },
    "actions_sticky_top": True
}