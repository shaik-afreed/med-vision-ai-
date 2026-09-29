import os

from alembic import command
from alembic.config import Config

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_migrations() -> None:
    """Equivalent of `alembic upgrade head`. The database URL comes from
    core.config.settings (alembic/env.py reads it), and the config path is
    absolute so this works regardless of the process's working directory."""
    config = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    config.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    command.upgrade(config, "head")
