"""Tests for opskit-secrets.py — secrets engine router."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "opskit"))

from opskit._cache import CACHE_DIR


@pytest.fixture
def secrets_setup(tmp_path, monkeypatch):
    """Set up a temporary secrets configuration."""
    test_cache = tmp_path / ".opskit"
    test_cache.mkdir()
    monkeypatch.setattr("opskit._cache.CACHE_DIR", test_cache)
    monkeypatch.setattr("opskit._cache.LAST_DISCOVERY_FILE", test_cache / "cache.json")
    monkeypatch.setattr("opskit._cache.LAST_USED_FILE", test_cache / "last-used.json")
    return test_cache


class TestEngineResolution:
    """Test secrets engine resolution from config."""

    def test_default_engine_is_bitwarden(self, secrets_setup):
        # No config files — should default to bitwarden
        from bin.opskit_secrets import _resolve_engine
        engine = _resolve_engine()
        assert engine == "bitwarden"

    def test_global_config_override(self, secrets_setup):
        import yaml
        global_config = secrets_setup / "secrets.yml"
        global_config.write_text("engine: env\nenv_var: MY_SESSION\n")

        from bin.opskit_secrets import _resolve_engine
        engine = _resolve_engine()
        assert engine == "env"

    def test_per_project_override(self, secrets_setup):
        import yaml
        # Create global config
        global_config = secrets_setup / "secrets.yml"
        global_config.write_text("engine: bitwarden\n")

        # Create per-project config
        project_dir = secrets_setup / "projects" / "test-project"
        project_dir.mkdir(parents=True)
        project_config = project_dir / "secrets.yml"
        project_config.write_text("engine: env\n")

        from bin.opskit_secrets import _resolve_engine
        engine = _resolve_engine("test-project")
        assert engine == "env"


class TestBitwardenSession:
    """Test bitwarden session resolution."""

    def test_reads_session_from_file(self, secrets_setup):
        # Create session file
        session_file = Path.home() / ".cache" / "opskit" / "bw-session"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text("test-session-token-12345")

        from bin.opskit_secrets import resolve_bitwarden_session
        session = resolve_bitwarden_session()
        assert session == "test-session-token-12345"

        # Clean up
        session_file.unlink(missing_ok=True)

    def test_returns_empty_when_no_session_file(self, secrets_setup):
        from bin.opskit_secrets import resolve_bitwarden_session
        session = resolve_bitwarden_session()
        assert session == ""


class TestEnvSecret:
    """Test env secret resolution."""

    def test_reads_from_env_var(self, secrets_setup, monkeypatch):
        monkeypatch.setenv("MY_TEST_SECRET", "env-secret-value")

        from bin.opskit_secrets import resolve_env_secret
        secret = resolve_env_secret("MY_TEST_SECRET")
        assert secret == "env-secret-value"

    def test_returns_none_when_var_not_set(self, secrets_setup, monkeypatch):
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)

        from bin.opskit_secrets import resolve_env_secret
        secret = resolve_env_secret("NONEXISTENT_VAR")
        assert secret == ""


class TestMainDispatch:
    """Test main argument parsing and dispatch."""

    def test_script_help(self):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "bin" / "opskit-secrets.py"), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "secret_name" in result.stdout
