from setuptools import setup, find_packages

import django_ledger

setup(
    name='django-ledger',
    version=django_ledger.__version__,
    packages=find_packages(exclude=['djltest']),
    url=django_ledger.__url__,
    license=django_ledger.__license__,
    keywords='django, finance, accounting, balance sheet, income statement, general ledger, money, engine',
    author=django_ledger.__author__,
    author_email=django_ledger.__email__,
    description='Financial analysis backend for Django. Balance Sheet, Income Statements, Chart of Accounts, Entities',
    include_package_data=True,
    use_pipfile=True,
    install_requires=[
        'django',
        'django-mptt',
        'ofxtools',
        'faker'
    ],
    project_urls={
        # 'Bug Tracker': 'https://bugs.example.com/HelloWorld/',
        # 'Documentation': 'https://docs.example.com/HelloWorld/',
        'Source Code': 'https://github.com/arrobalytics/django-ledger',
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Office/Business :: Financial :: Accounting',
        'Development Status :: 3 - Alpha',
        'Framework :: Django :: 3.0',
        'Intended Audience :: Financial and Insurance Industry',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
    ]
)
