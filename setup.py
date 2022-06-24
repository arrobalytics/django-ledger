from setuptools import setup, find_packages

import django_ledger

setup(
    dependency_links=[
    ],
    name="django-ledger",
    version=django_ledger.__version__,
    packages=find_packages(exclude=["assets", "dev_env"]),
    url=django_ledger.__url__,
    license=django_ledger.__license__,
    keywords="django, finance, bookkeeping, accounting, balance sheet, income statement, general ledger, money, engine",
    author=django_ledger.__author__,
    author_email=django_ledger.__email__,
    description="Bookkeeping & Financial analysis backend for Django. Balance Sheet, Income Statements, "
                + "Chart of Accounts, Entities",
    include_package_data=True,
    install_requires=['aniso8601==7.0.0', "asgiref==3.5.2; python_version >= '3.7'", 'django==3.2.13',
                      "django-filter==22.1; python_version >= '3.7'", 'django-graphql-auth[graphql]==0.3.16',
                      "django-graphql-jwt==0.3.0; python_version >= '3.6' and python_version < '4'",
                      'django-treebeard==4.5.1', 'faker==8.16.0', 'graphene==2.1.9', 'graphene-django[graphql]==2.15.0',
                      "graphql-core==2.3.2; python_version >= '3.6' and python_version < '4'",
                      "graphql-relay==2.0.1; python_version >= '3.6' and python_version < '4'", 'markdown==3.3.7',
                      'ofxtools==0.9.5', 'pillow==9.1.1', 'promise==2.3', "pyjwt==1.7.1; python_version >= '3.6'",
                      "python-dateutil==2.8.2; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
                      'pytz==2022.1', 'rx==1.6.1', "singledispatch==3.7.0; python_version >= '2.6'",
                      "six==1.16.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
                      "sqlparse==0.4.2; python_version >= '3.5'", 'text-unidecode==1.3'],
    project_urls={
        "Bug Tracker": "https://github.com/arrobalytics/django-ledger/issues",
        # 'Documentation': 'https://docs.example.com/HelloWorld/',
        "Source Code": "https://github.com/arrobalytics/django-ledger",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Office/Business :: Financial :: Accounting",
        "Development Status :: 3 - Alpha",
        "Framework :: Django :: 3.0",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    ],
)
