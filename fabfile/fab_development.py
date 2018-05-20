# -*- coding: utf-8 -*-

from fabric.operations import local

from fabfile import env, apps
from fabfile.utils import grint, grintify

EMAIL_URL = 'https://raw.githubusercontent.com/SavandBros/gonevis-emails/master/emails/'


@grintify
def manage_local(cmd):
    """
    Run manage.py on local.
    """
    local(f'python manage.py {cmd}')


@grintify
def set_env(env_name):
    """
    Set `env.env_name`.
    """
    grint(f'Set env_name to {env_name}')
    env.env_name = env_name


@grintify
def makemigrations():
    """Make schema migrations for all the installed app."""
    manage_local('makemigrations {0}'.format(' '.join(apps)))


@grintify
def migrate():
    """Run django migrate"""
    manage_local('migrate')


@grintify
def clean_pyc():
    """Clean python compiled files (*.pyc)."""
    local("find %(root)s/ -name '*.pyc' -delete" % env)


@grintify
def check():
    """Validate the local project."""
    grint('Validating the local source code...')
    manage_local('check')


@grintify
def cq():
    """Ensuring code quality."""
    local('flake8 --config=flake8.ini')
    grint("****\n\t***PASSED CODE QUALITY CHECK, AWESOME!!!***\n****")


@grintify
def req():
    """Install Python Development Requirements"""
    local('pip install -r requirements/dev.txt')
