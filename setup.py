from setuptools import setup, find_namespace_packages

PACKAGES = find_namespace_packages(exclude=["dev_env", "docs", "assets", "docs.source", "notebooks"])

setup(packages=PACKAGES)
