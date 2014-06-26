from __future__ import print_function
import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand


def read_long_description(filename="README.rst"):
    with open(filename) as f:
        return f.read().strip()


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errcode = pytest.main(self.test_args)
        sys.exit(errcode)

setup(
    name='job_progress',
    version='0.0.7',
    url='https://github.com/uber/job_progress',
    license='Proprietary',
    author='Charles-Axel Dein',
    tests_require=['pytest'],
    cmdclass={'test': PyTest},
    author_email='charles@uber.com',
    description='Provide a JobProgress object',
    long_description=read_long_description(),
    packages=['job_progress'],
    include_package_data=True,
    platforms='any',
    test_suite='job_progress.tests',
    zip_safe=False,
    keywords=["jobs", "tasks"],
    classifiers=[
        'Programming Language :: Python',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet :: WWW/HTTP',
        ],
)
