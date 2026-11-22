"""
Tests for the Django Ledger version string.

These tests check that pyproject.toml is the one source of truth for the version: the package, the template
context and the current_version template tag all report the same value, and the lookup falls back in the right
order when pyproject.toml is missing or belongs to another project.
"""

import tomllib
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import RequestFactory, SimpleTestCase

from django_ledger import __version__
from django_ledger.context import django_ledger_context
from django_ledger.templatetags.django_ledger import current_version
from django_ledger.version import PACKAGE_NAME, PYPROJECT_PATH, UNKNOWN_VERSION, PackageVersion

MISSING_PACKAGE_NAME: str = 'django-ledger-not-installed'


class PyprojectFileMixIn:
    """
    Writes a throwaway pyproject.toml into a temporary directory for the length of one test.
    """

    def make_pyproject(self, content: str) -> Path:
        """
        Writes the given TOML text to a pyproject.toml in a fresh temporary directory and returns its path.
        The directory is removed when the test finishes.
        """
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        pyproject_path = Path(temp_dir.name) / 'pyproject.toml'
        pyproject_path.write_text(content, encoding='utf-8')
        return pyproject_path


class VersionSourceOfTruthTest(SimpleTestCase):
    """
    Checks that every place Django Ledger shows its version agrees with pyproject.toml.
    """

    def setUp(self) -> None:
        """
        Reads the project version straight from the repository's pyproject.toml.
        """
        with PYPROJECT_PATH.open('rb') as pyproject_file:
            self.pyproject_version: str = tomllib.load(pyproject_file)['project']['version']

    def test_package_version_matches_pyproject(self) -> None:
        """
        The package's __version__ is the version written in pyproject.toml.
        """
        self.assertEqual(__version__, self.pyproject_version)

    def test_template_context_reports_package_version(self) -> None:
        """
        The VERSION value in the template context is the package version.
        """
        request = RequestFactory().get('/')
        self.assertEqual(django_ledger_context(request)['VERSION'], self.pyproject_version)

    def test_current_version_tag_reports_package_version(self) -> None:
        """
        The current_version template tag returns the package version.
        """
        self.assertEqual(current_version(), self.pyproject_version)


class PackageVersionLookupTest(PyprojectFileMixIn, SimpleTestCase):
    """
    Checks the order PackageVersion uses to find a version and what it does when a source is missing.
    """

    def test_reads_version_from_matching_pyproject(self) -> None:
        """
        A pyproject.toml that names this package supplies the version, four-part point releases included.
        """
        pyproject_path = self.make_pyproject(f'[project]\nname = "{PACKAGE_NAME}"\nversion = "1.2.3.4"\n')
        self.assertEqual(PackageVersion(pyproject_path=pyproject_path).resolve(), '1.2.3.4')

    def test_ignores_pyproject_of_another_project(self) -> None:
        """
        A pyproject.toml for a different project is skipped, so its version is never reported as ours.
        """
        pyproject_path = self.make_pyproject('[project]\nname = "host-project"\nversion = "9.9.9"\n')
        lookup = PackageVersion(package_name=MISSING_PACKAGE_NAME, pyproject_path=pyproject_path)
        self.assertIsNone(lookup.from_pyproject())
        self.assertEqual(lookup.resolve(), UNKNOWN_VERSION)

    def test_ignores_unreadable_pyproject(self) -> None:
        """
        A pyproject.toml that is not valid TOML is treated the same as a missing one.
        """
        pyproject_path = self.make_pyproject('[project\nname = ')
        self.assertIsNone(PackageVersion(pyproject_path=pyproject_path).from_pyproject())

    def test_falls_back_to_placeholder_without_any_source(self) -> None:
        """
        With no pyproject.toml and no installed distribution, the placeholder local version is returned.
        """
        pyproject_path = self.make_pyproject('')
        pyproject_path.unlink()
        lookup = PackageVersion(package_name=MISSING_PACKAGE_NAME, pyproject_path=pyproject_path)
        self.assertIsNone(lookup.from_pyproject())
        self.assertIsNone(lookup.from_metadata())
        self.assertEqual(lookup.resolve(), UNKNOWN_VERSION)
