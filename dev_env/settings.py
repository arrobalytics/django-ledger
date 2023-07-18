import os
from pathlib import Path

from django_ledger.settings import DJANGO_LEDGER_GRAPHQL_SUPPORT_ENABLED

BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    SECRET_KEY = 'djangoledger1234!DoNotUse!BadIdea!VeryInsecure!'
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', '192.168.1.101', 'localhost']
CSRF_TRUSTED_ORIGINS = ['https://*.preview.app.github.dev']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_ledger',
]

if DJANGO_LEDGER_GRAPHQL_SUPPORT_ENABLED:
    INSTALLED_APPS += [
        'graphene_django',
        'oauth2_provider'
    ]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'dev_env.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'dev_env.wsgi.application'

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

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

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

# TIME_ZONE = 'US/Eastern'
TIME_ZONE = 'US/Eastern'

USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'
LOGIN_URL = '/auth/login/'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

if DJANGO_LEDGER_GRAPHQL_SUPPORT_ENABLED:
    GRAPHENE = {
        'SCHEMA': 'django_ledger.contrib.django_ledger_graphene.api.schema',
        'SCHEMA_OUTPUT': '../django_ledger/contrib/django_ledger_graphene/schema.graphql',  # defaults to schema.json,
        # 'SCHEMA_INDENT': 2,  # Defaults to None (displays all data on a single line)
        # 'MIDDLEWARE': [
        #     'graphql_jwt.middleware.JSONWebTokenMiddleware',
        # ],
    }

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
