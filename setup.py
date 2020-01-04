from setuptools import setup, find_packages

import django_ledger

setup(
    name='django-ledger',
    version=django_ledger.__version__,
    packages=find_packages(),
    url=django_ledger.__url__,
    license=django_ledger.__license__,
    keywords='django, finance, accounting, balance sheet, income, statement, general, ledger, money, engine',
    author=django_ledger.__author__,
    author_email=django_ledger.__email__,
    description='Financial analysis backend for Django. Balance Sheet, Income Statements, Chart of Accounts, Entities',
    install_requires=[
        'django'
        'django-mptt',
    ],
    project_urls={
        # "Bug Tracker": "https://bugs.example.com/HelloWorld/",
        # "Documentation": "https://docs.example.com/HelloWorld/",
        # "Source Code": "https://github.com/elarroba/django-ledger",
    }
)
