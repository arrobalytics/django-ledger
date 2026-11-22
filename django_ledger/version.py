"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Works out the Django Ledger version from one source of truth: the version field in pyproject.toml.

A source checkout reads pyproject.toml directly, so the version is right even when the project was never installed.
An installed copy reads the version the packaging tools recorded from that same field when the package was built.
"""

import tomllib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as installed_version
from pathlib import Path

PACKAGE_NAME: str = 'django-ledger'
PYPROJECT_PATH: Path = Path(__file__).resolve().parent.parent / 'pyproject.toml'
UNKNOWN_VERSION: str = '0+unknown'


class PackageVersion:
    """
    Looks up the version of a package, first from the pyproject.toml of a source checkout and then from the
    metadata of an installed distribution.

    Parameters
    ----------
    package_name: str
        The distribution name as written in pyproject.toml. Defaults to django-ledger.
    pyproject_path: Path
        Where a source checkout keeps its pyproject.toml. Defaults to the file next to the django_ledger package.
    """

    def __init__(self, package_name: str = PACKAGE_NAME, pyproject_path: Path = PYPROJECT_PATH) -> None:
        self.package_name: str = package_name
        self.pyproject_path: Path = pyproject_path

    def from_pyproject(self) -> str | None:
        """
        Reads the version from pyproject.toml. Returns None when the file is missing or unreadable, or when it
        belongs to a different project, so a host project's own pyproject.toml is never mistaken for ours.
        """
        try:
            with self.pyproject_path.open('rb') as pyproject_file:
                project = tomllib.load(pyproject_file).get('project', {})
        except (OSError, tomllib.TOMLDecodeError):
            return None

        if project.get('name') != self.package_name:
            return None
        return project.get('version')

    def from_metadata(self) -> str | None:
        """
        Reads the version recorded for the installed distribution. Returns None when the package is not installed.
        """
        try:
            return installed_version(self.package_name)
        except PackageNotFoundError:
            return None

    def resolve(self) -> str:
        """
        Returns the first version found, checking the source checkout before the installed metadata. Falls back to
        a placeholder local version when neither is available.
        """
        return self.from_pyproject() or self.from_metadata() or UNKNOWN_VERSION


VERSION: str = PackageVersion().resolve()
