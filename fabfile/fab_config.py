"""Fabric config file."""
from typing import Tuple, List

import os
from fabric.api import env

env.use_ssh_config = True

# Project
env.root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
env.project_name: str = 'whisper'
env.django_project_dir: str = 'whisper'
env.project_path: str = env.root
env.repo_prod: str = 'heroku'

apps: List[str] = ['chat', 'users', ]


localization_dirs: List[str] = apps + ['templates', 'whisper', ]
translations: Tuple[str] = ('en', 'fa', )
