from distutils.core import setup

setup(
    name='django-ledger',
    version='0.0.1',
    packages=['django_ledger', 'django_ledger.models', 'django_ledger.models.io',
              'django_ledger.models.mixins', 'django_ledger.migrations'],
    url='http://djangoledger.io',
    license='MIT',
    author='Miguel Sanda',
    author_email='msanda@arrobalytics.com',
    description='Financial analysis backend for Django'
)
