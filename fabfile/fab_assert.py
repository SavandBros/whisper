# -*- coding: utf-8 -*-
"""Fab assert, testing and code quality tasks."""
from typing import Optional

import psycopg2
import shutil
from distutils.util import strtobool
from fabric.operations import local, os

from fabfile import fab_config
from fabfile import fab_development
from fabfile.utils import grintify

CONFIRM_POSITIVE = ['yes', 'y', 'yeah', ]
COVERAGE_REPORT_HTML_DIR = 'coverage_html'
COVERAGE_REPORT_FILE = '.coverage'


def get_apps_tests(app_name: Optional[str] = '', exclude: Optional[str] = None) -> str:
    """
    Creating a app or test case name list.

    :param app_name: Application or test case name.
    :param exclude: Exclude an application from testing.
    """
    if app_name not in ['', None]:
        app_name = app_name.replace('/', '.').replace('.py', '')

    if exclude:
        apps = fab_config.apps
        apps.remove(exclude)

        return ' '.join(apps)

    return app_name


def get_test_command(app_name: Optional[str] = '',
                     keep_db: Optional[bool] = True,
                     parallel: Optional[bool] = True,
                     fake_migrations: Optional[bool] = True,
                     exclude: Optional[str] = None) -> str:
    """
    Creating the test command for ``manage.py``.

    :param app_name: App name to run the tests against
    :param keep_db: To keep the db and not destroy it.
        This will optimize the test time.
    :param parallel: To run the tests in parallel.
        This will optimize the test time.
    :param fake_migrations: Faking the migration instead of actually
        running them.
        This will optimize the test time.
    :param exclude: Exclude an application from testing.
    """
    base_command = 'test {0}'.format(get_apps_tests(app_name, exclude))
    args = [
        # '--settings=whisper.settings.testing',
    ]

    if fake_migrations:
        os.environ.setdefault('DJANGO_FAKE_MIGRATIONS', 'YES')

    if keep_db:
        args.append('-k')

    if parallel:
        args.append('--parallel 6')

    return '{base_command} --noinput -v3 {args}'.format(
        base_command=base_command, args=' '.join(args)
    )


# noinspection SqlNoDataSourceInspection
@grintify
def initialize_db() -> None:
    """Initialize Testing Database."""
    db_name = 'test_whisper'
    db_user = os.environ.get('PG_USER', 'postgres')
    db_password = os.environ.get('PG_PASSWORD', 'pass')

    def create_connection(db_name: str ='template1'):
        conn = psycopg2.connect(f"dbname='{db_name}' user='{db_user}' host='localhost' password='{db_password}'")
        conn.set_isolation_level(0)

        return conn

    conn = create_connection()

    try:
        conn.cursor().execute(f'create database {db_name}')
    except psycopg2.ProgrammingError:
        conn.cursor().execute(f'drop database {db_name}')
        conn.cursor().execute(f'create database {db_name}')


@grintify
def coverage() -> None:
    """Code coverage report."""
    if os.path.exists(COVERAGE_REPORT_HTML_DIR):
        shutil.rmtree(COVERAGE_REPORT_HTML_DIR)

    if os.path.isfile(COVERAGE_REPORT_FILE):
        os.remove(COVERAGE_REPORT_FILE)

    initialize_db()
    local("coverage run --source='.' manage.py {0}".format(get_test_command(
        parallel=False, fake_migrations=False
    )))

    local("coverage report --skip-covered")
    local("coverage html")


def test(app_name: Optional[str] = '', exclude: Optional[str] = None,
         parallel: Optional[str] = 'y', fake_db: Optional[str] = 'y',
         keep_db: Optional[str] = 'y', log_off: Optional[str] = 'y',
         haystack_silent: Optional[str] = 'y') -> None:
    """Running the tests."""
    parallel = bool(strtobool(parallel))
    fake_db = bool(strtobool(fake_db))
    keep_db = bool(strtobool(keep_db))
    log_off = bool(strtobool(log_off))
    haystack_silent = bool(strtobool(haystack_silent))

    if not keep_db:
        fake_db = False

    if log_off:
        os.environ.setdefault('WHISPER_TESTING_SHOW_LOGS', 'NO')

    if haystack_silent in CONFIRM_POSITIVE:
        os.environ.setdefault('DJANGO_HAYSTACK_SILENT', 'YES')

    fab_development.manage_local(
        get_test_command(
            app_name=app_name, keep_db=keep_db, parallel=parallel,
            fake_migrations=fake_db, exclude=exclude
        )
    )
