"""Tests for bin/opskit-secrets.py — secrets engine router.

The module is imported (not exec'd) so config paths and the vault
resolver can be redirected without touching the live vault.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))


def _load():
    spec = importlib.util.spec_from_file_location(
        "opskit_secrets", _ROOT / "bin" / "opskit-secrets.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def secrets(tmp_path, monkeypatch):
    module = _load()
    monkeypatch.setattr(module, "GLOBAL_SECRETS_FILE", tmp_path / "secrets.yml")
    monkeypatch.setattr(module, "PROJECT_SECRETS_DIR", tmp_path / "projects")
    return module


class TestEngineResolution:
    def test_default_engine_is_bitwarden(self, secrets):
        assert secrets._resolve_engine() == "bitwarden"

    def test_global_engine_config(self, secrets):
        secrets.GLOBAL_SECRETS_FILE.write_text("engine: env\nenv_var: X\n")
        assert secrets._resolve_engine() == "env"

    def test_project_override_wins(self, secrets, tmp_path):
        secrets.GLOBAL_SECRETS_FILE.write_text("engine: env\n")
        proj = secrets.PROJECT_SECRETS_DIR / "myproj"
        proj.mkdir(parents=True)
        (proj / "secrets.yml").write_text("engine: bitwarden\n")
        assert secrets._resolve_engine(str(tmp_path / "myproj")) == "bitwarden"


class TestEnvSecret:
    def test_reads_configured_env_var(self, secrets, monkeypatch):
        secrets.GLOBAL_SECRETS_FILE.write_text("engine: env\nenv_var: OPSKIT_TEST_SECRET\n")
        monkeypatch.setenv("OPSKIT_TEST_SECRET", "s3cr3t")
        assert secrets.resolve_env_secret() == "s3cr3t"

    def test_missing_env_var_config_returns_none(self, secrets):
        assert secrets.resolve_env_secret() is None


class TestVaultDelegation:
    def test_resolves_via_bw_session_token(self, secrets, monkeypatch):
        calls = []

        class _R:
            def __init__(self, rc=0, out=""):
                self.returncode = rc
                self.stdout = out
                self.stderr = ""

        def fake_run(cmd, **kw):
            calls.append(cmd)
            if any("bw_session.py" in str(c) for c in cmd):
                return _R(0, "TOKEN123\n")
            return _R(0, "")

        monkeypatch.setattr(secrets.subprocess, "run", fake_run)
        assert secrets.resolve_bitwarden_session() == "TOKEN123"
        assert any("bw_session.py" in str(c) and "--token" in c for c in calls)
