from distutils.core import setup

setup(
    name='django-ledger',
    version='0.1',
    packages=['django-ledger', 'django-ledger.api', 'django-ledger.models', 'django-ledger.models.io',
              'django-ledger.models.mixins', 'django-ledger.models.actions', 'django-ledger.migrations',
              'django-ledger.templatetags'],
    url='http://djangoledger.io',
    license='MIT',
    author='Miguel Sanda',
    author_email='msanda@arrobalytics.com',
    description='Django application...'
)
