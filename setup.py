from setuptools import setup, find_packages

import django_ledger

setup(
    extras_require={"dev": ['sphinx~=4.5.0', 'behave~=1.2.6', 'pipenv-setup', 'pylint', 'furo', ]},
    dependency_links=[],
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
    install_requires=[
        'django>=3.2',
        'django-treebeard~=4.5.1',
        'ofxtools~=0.9.4',
        'markdown~=3.3.4',
        'faker~=8.12',
        'pillow>=8.4.0'
    ],
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
    ]
)
