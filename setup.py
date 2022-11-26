from setuptools import setup, find_packages, find_namespace_packages

import django_ledger

PACKAGES = find_namespace_packages(exclude=["dev_env", "docs", "assets", "docs.source"])

setup(
    extras_require={
        "dev": ["sphinx~=4.5.0", "behave~=1.2.6", "pipenv-setup", "pylint", "furo"]
    },
    dependency_links=[],
    name="django-ledger",
    version=django_ledger.__version__,
    packages=PACKAGES,
    url=django_ledger.__url__,
    license=django_ledger.__license__,
    keywords="django, finance, bookkeeping, accounting, balance sheet, income statement, general ledger, money, engine",
    author=django_ledger.__author__,
    author_email=django_ledger.__email__,
    description="Bookkeeping & Financial analysis backend for Django. Balance Sheet, Income Statements, "
    + "Chart of Accounts, Entities",
    include_package_data=True,
    install_requires=[
        "asgiref==3.5.2; python_version >= '3.7'",
        "django==4.1.3",
        "django-treebeard==4.5.1",
        "faker==15.3.3",
        "markdown==3.4.1",
        "ofxtools==0.9.5",
        "pillow==9.3.0",
        "python-dateutil==2.8.2; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "six==1.16.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "sqlparse==0.4.3; python_version >= '3.5'",
        "text-unidecode==1.3",
        "tzdata==2022.2; sys_platform == 'win32'",
    ],
    project_urls={
        "Bug Tracker": "https://github.com/arrobalytics/django-ledger/issues",
        "Documentation": "https://docs.djangoledger.com",
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
