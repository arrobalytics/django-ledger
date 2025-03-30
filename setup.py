from setuptools import find_namespace_packages, setup

PACKAGES = find_namespace_packages(exclude=["dev_env", "docs", "assets", "docs.source", "notebooks"])

setup(packages=PACKAGES)
