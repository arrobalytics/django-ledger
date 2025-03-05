import os
from pathlib import Path

from django_ledger.settings import DJANGO_LEDGER_GRAPHQL_SUPPORT_ENABLED

BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    SECRET_KEY = 'djangoledger1234!DoNotUse!BadIdea!VeryInsecure!'
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', '192.168.1.102', 'localhost']
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

USE_TZ = True
TIME_ZONE = 'America/New_York'

USE_I18N = True
USE_L10N = True

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

    OAUTH2_PROVIDER = {
        'OAUTH2_BACKEND_CLASS': 'oauth2_provider.oauth2_backends.JSONOAuthLibCore',
    }

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379',
    }
}

# LOGGING = {
#     'version': 1,
#     'filters': {
#         'require_debug_true': {
#             '()': 'django.utils.log.RequireDebugTrue',
#         }
#     },
#     'handlers': {
#         'console': {
#             'level': 'DEBUG',
#             'filters': ['require_debug_true'],
#             'class': 'logging.StreamHandler',
#         }
#     },
#     'loggers': {
#         'django.db.backends': {
#             'level': 'DEBUG',
#             'handlers': ['console'],
#         }
#     }
# }

# DJANGO_LEDGER_ACCOUNT_MODEL = getattr(settings, 'DJANGO_LEDGER_ACCOUNT_MODEL', 'django_ledger.AccountModel')
# DJANGO_LEDGER_CHART_OF_ACCOUNTS_MODEL = getattr(settings, 'DJANGO_LEDGER_ACCOUNT_MODEL', 'django_ledger.ChartOfAccountModel')
# DJANGO_LEDGER_TRANSACTION_MODEL = getattr(settings, 'DJANGO_LEDGER_TRANSACTION_MODEL', 'django_ledger.TransactionModel')
# DJANGO_LEDGER_JOURNAL_ENTRY_MODEL = getattr(settings, 'DJANGO_LEDGER_JOURNAL_ENTRY_MODEL', 'django_ledger.JournalEntryModel')
# DJANGO_LEDGER_LEDGER_MODEL = getattr(settings, 'DJANGO_LEDGER_LEDGER_MODEL', 'django_ledger.LedgerModel')
# DJANGO_LEDGER_ENTITY_MODEL = getattr(settings, 'DJANGO_LEDGER_ENTITY_MODEL', 'django_ledger.EntityModel')
# DJANGO_LEDGER_ENTITY_STATE_MODEL = getattr(settings, 'DJANGO_LEDGER_ENTITY_STATE_MODEL', 'django_ledger.EntityStateModel')
# DJANGO_LEDGER_ENTITY_UNIT_MODEL = getattr(settings, 'DJANGO_LEDGER_ENTITY_UNIT_MODEL', 'django_ledger.EntityUnitModel')
# DJANGO_LEDGER_ESTIMATE_MODEL = getattr(settings, 'DJANGO_LEDGER_ESTIMATE_MODEL', 'django_ledger.EstimateModel')
# DJANGO_LEDGER_BILL_MODEL = getattr(settings, 'DJANGO_LEDGER_BILL_MODEL', 'django_ledger.BillModel')
# DJANGO_LEDGER_INVOICE_MODEL = getattr(settings, 'DJANGO_LEDGER_INVOICE_MODEL', 'django_ledger.InvoiceModel')
# DJANGO_LEDGER_PURCHASE_ORDER_MODEL = getattr(settings, 'DJANGO_LEDGER_PURCHASE_ORDER_MODEL', 'django_ledger.PurchaseOrderModel')
# DJANGO_LEDGER_CUSTOMER_MODEL = getattr(settings, 'DJANGO_LEDGER_CUSTOMER_MODEL', 'django_ledger.CustomerModel')
# DJANGO_LEDGER_VENDOR_MODEL = getattr(settings, 'DJANGO_LEDGER_VENDOR_MODEL', 'django_ledger.VendorModel')
# DJANGO_LEDGER_BANK_ACCOUNT_MODEL = getattr(settings, 'DJANGO_LEDGER_BANK_ACCOUNT_MODEL', 'django_ledger.BankAccountModel')
# DJANGO_LEDGER_CLOSING_ENTRY_MODEL = getattr(settings, 'DJANGO_LEDGER_CLOSING_ENTRY_MODEL', 'django_ledger.ClosingEntryModel')
# DJANGO_LEDGER_UNIT_OF_MEASURE_MODEL = getattr(settings, 'DJANGO_LEDGER_UNIT_OF_MEASURE_MODEL', 'django_ledger.UnitOfMeasureModel')
# DJANGO_LEDGER_ITEM_TRANSACTION_MODEL = getattr(settings, 'DJANGO_LEDGER_ITEM_TRANSACTION_MODEL', 'django_ledger.ItemTransactionModel')
# DJANGO_LEDGER_ITEM_MODEL = getattr(settings, 'DJANGO_LEDGER_ITEM_MODEL', 'django_ledger.ItemModel')
# DJANGO_LEDGER_STAGED_TRANSACTION_MODEL = getattr(settings, 'DJANGO_LEDGER_STAGED_TRANSACTION_MODEL', 'django_ledger.StagedTransactionModel')
# DJANGO_LEDGER_IMPORT_JOB_MODEL = getattr(settings, 'DJANGO_LEDGER_IMPORT_JOB_MODEL', 'django_ledger.ImportJobModel')

# DJANGO_LEDGER_ACCOUNT_MODEL = 'django_ledger.AccountModel'
# DJANGO_LEDGER_CHART_OF_ACCOUNTS_MODEL = 'django_ledger.ChartOfAccountModel'
# DJANGO_LEDGER_TRANSACTION_MODEL = 'django_ledger.TransactionModel'
# DJANGO_LEDGER_JOURNAL_ENTRY_MODEL = 'django_ledger.JournalEntryModel'
# DJANGO_LEDGER_LEDGER_MODEL = 'django_ledger.LedgerModel'
# DJANGO_LEDGER_ENTITY_MODEL = 'django_ledger.EntityModel'
# DJANGO_LEDGER_ENTITY_STATE_MODEL = 'django_ledger.EntityStateModel'
# DJANGO_LEDGER_ENTITY_UNIT_MODEL = 'django_ledger.EntityUnitModel'
# DJANGO_LEDGER_ESTIMATE_MODEL = 'django_ledger.EstimateModel'
# DJANGO_LEDGER_BILL_MODEL = 'django_ledger.BillModel'
# DJANGO_LEDGER_INVOICE_MODEL = 'django_ledger.InvoiceModel'
# DJANGO_LEDGER_PURCHASE_ORDER_MODEL = 'django_ledger.PurchaseOrderModel'
# DJANGO_LEDGER_CUSTOMER_MODEL = 'django_ledger.CustomerModel'
# DJANGO_LEDGER_VENDOR_MODEL = 'django_ledger.VendorModel'
# DJANGO_LEDGER_BANK_ACCOUNT_MODEL = 'django_ledger.BankAccountModel'
# DJANGO_LEDGER_CLOSING_ENTRY_MODEL = 'django_ledger.ClosingEntryModel'
# DJANGO_LEDGER_CLOSING_ENTRY_TRANSACTION_MODEL = 'django_ledger.ClosingEntryTransactionModel'
# DJANGO_LEDGER_UNIT_OF_MEASURE_MODEL = 'django_ledger.UnitOfMeasureModel'
# DJANGO_LEDGER_ITEM_TRANSACTION_MODEL = 'django_ledger.ItemTransactionModel'
# DJANGO_LEDGER_ITEM_MODEL = 'django_ledger.ItemModel'
# DJANGO_LEDGER_STAGED_TRANSACTION_MODEL = 'django_ledger.StagedTransactionModel'
# DJANGO_LEDGER_IMPORT_JOB_MODEL = 'django_ledger.ImportJobModel'
