"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>

Shared test harness pieces.

SeededTestMixIn makes the random data in the test suite repeatable. It seeds Python's random module, and Faker
when it is installed, from one TEST_SEED constant: once before the class-level fixtures are built and again before
every test method. The same seed always produces the same entities, documents and amounts, so a failure can be
reproduced by running the suite again.

requires_faker skips tests that need Faker, which comes with the test and demo extras, when it is not installed.
"""

from random import seed as seed_random
from typing import Optional
from unittest import skipUnless

from django_ledger.demo import FAKER_INSTALLED

try:
    from faker import Faker
except ImportError:
    Faker = None

TEST_SEED: int = 42

FAKER_REQUIRED_REASON: str = 'Needs Faker. Install the test extra: pip install "django-ledger[test]"'

# Skips a test class or method when Faker is not installed, for tests that build data with EntityDataGenerator.
requires_faker = skipUnless(FAKER_INSTALLED, FAKER_REQUIRED_REASON)


class SeededTestMixIn:
    """
    Seeds random and Faker for a test case.

    Put it before the Django TestCase class in the bases. Subclasses can set TEST_SEED to a different integer to
    get another repeatable data set.
    """

    TEST_SEED: int = TEST_SEED

    @classmethod
    def seed_random_data(cls, seed: Optional[int] = None) -> None:
        """
        Seeds Python's random module, and Faker when it is installed, with the given seed or with TEST_SEED.
        """
        seed = cls.TEST_SEED if seed is None else seed
        seed_random(seed)
        if Faker is not None:
            Faker.seed(seed)

    @classmethod
    def setUpClass(cls) -> None:
        """
        Seeds before Django builds the class fixtures, so setUpTestData always sees the same random draws.
        """
        cls.seed_random_data()
        super().setUpClass()

    def run(self, result=None):
        """
        Seeds again before each test method runs, so a test's random choices don't depend on test order.
        """
        self.seed_random_data()
        return super().run(result)
