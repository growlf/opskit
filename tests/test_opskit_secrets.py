"""Tests for opskit-secrets.py — secrets engine router."""

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "opskit"))

# Reuse the secrets tests
from test_secrets import TestEngineResolution, TestBitwardenSession, TestEnvSecret, TestMainDispatch

class TestSecretsEngine(TestEngineResolution):
    """Test engine resolution."""
    pass

class TestSecretsBitwarden(TestBitwardenSession):
    """Test bitwarden session."""
    pass

class TestSecretsEnv(TestEnvSecret):
    """Test env secret."""
    pass

class TestSecretsDispatch(TestMainDispatch):
    """Test main dispatch."""
    pass
