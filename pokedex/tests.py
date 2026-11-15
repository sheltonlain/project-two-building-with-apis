"""Settings come from environment variables (a real environment wins over the local .env)."""

import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

PRINT_SETTINGS = (
    "import django; django.setup(); from django.conf import settings as s; "
    "print(s.SECRET_KEY, s.DEBUG, ','.join(s.ALLOWED_HOSTS))"
)


def run_with_env(**env_vars):
    env = {**os.environ, "DJANGO_SETTINGS_MODULE": "pokedex.settings", **env_vars}
    return subprocess.run(
        [sys.executable, "-c", PRINT_SETTINGS],
        cwd=BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


def test_settings_read_secret_key_debug_and_hosts_from_environment():
    result = run_with_env(
        DJANGO_SECRET_KEY="from-the-environment",
        DJANGO_DEBUG="false",
        DJANGO_ALLOWED_HOSTS="pokedex.example.com, www.pokedex.example.com",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == [
        "from-the-environment",
        "False",
        "pokedex.example.com,www.pokedex.example.com",
    ]


def test_missing_secret_key_is_refused_when_debug_is_off():
    result = run_with_env(DJANGO_SECRET_KEY="", DJANGO_DEBUG="false")

    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY must be set" in result.stderr


def test_dotenv_file_is_git_ignored():
    result = subprocess.run(
        ["git", "check-ignore", ".env"], cwd=BASE_DIR, capture_output=True, text=True
    )

    assert result.returncode == 0
