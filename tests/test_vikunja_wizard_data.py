"""Tests for bin/vikunja-wizard-data.py — vikunja-wizard-data command.

These tests import the script as a module and test its functions directly.
They require a live Vikunja server for full functionality, so we mock HTTP
calls and use VIKUNJA_BMS_TOKEN to avoid the mcp-run.sh dependency.
"""
import json
import os
import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

# Dynamic import: load the script module without modifying sys.path at module level
_REPO_ROOT = Path(__file__).resolve().parent.parent
_BIN = _REPO_ROOT / "bin"
_spec = __import__("importlib.util").util.spec_from_file_location(
    "vikunja_wizard_data", _BIN / "vikunja-wizard-data.py"
)
wizard = __import__("importlib.util").util.module_from_spec(_spec)
_spec.loader.exec_module(wizard)
sys.modules["vikunja_wizard_data"] = wizard


class TestVikunjaWizardData(unittest.TestCase):
    """Test vikunja-wizard-data script functionality.

    Uses mocked HTTP responses since the script requires a live
    Vikunja server. Tests verify JSON output structure and error handling.
    """

    def setUp(self):
        """Set up test environment with a mock tenant."""
        self.env = os.environ.copy()
        self.env.pop("VIKUNJA_BMS_TOKEN", None)
        # Create a temporary tenants file for load_tenants()
        self.tenants_file = _REPO_ROOT / "mcp" / "tenants-vikunja.local.json"
        self.tenants_file.write_text(
            json.dumps({"bms": {"base_url": "http://localhost:3456"}})
        )

    def tearDown(self):
        """Clean up temporary tenants file."""
        if self.tenants_file.exists():
            self.tenants_file.unlink()

    @mock.patch("vikunja_wizard_data.resolve_token")
    @mock.patch("requests.get")
    def test_cmd_projects_output(self, mock_get, mock_token):
        """test_vikunja_wizard_cmd_projects: cmd_projects outputs valid JSON list."""
        mock_token.return_value = "test-token"
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": 1, "title": "Test Project", "description": "Test"},
        ]
        mock_response.headers = {}
        mock_get.return_value = mock_response

        with mock.patch("sys.stdout", new=StringIO()) as fake_out:
            wizard.cmd_projects()

        output = json.loads(fake_out.getvalue())
        self.assertIsInstance(output, list)
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]["id"], 1)
        mock_get.assert_called_once_with(
            "http://localhost:3456/api/v1/projects",
            headers={"Authorization": "Bearer test-token"},
            timeout=15,
        )

    @mock.patch("vikunja_wizard_data.resolve_token")
    @mock.patch("requests.get")
    def test_cmd_users_output(self, mock_get, mock_token):
        """test_vikunja_wizard_cmd_users: cmd_users outputs user list with query param."""
        mock_token.return_value = "test-token"
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": 1, "username": "testuser", "display_name": "Test User"},
        ]
        mock_response.headers = {}
        mock_get.return_value = mock_response

        with mock.patch("sys.stdout", new=StringIO()) as fake_out:
            wizard.cmd_users("test")

        output = json.loads(fake_out.getvalue())
        self.assertIsInstance(output, list)
        self.assertEqual(output[0]["username"], "testuser")
        mock_get.assert_called_once_with(
            "http://localhost:3456/api/v1/users?s=test",
            headers={"Authorization": "Bearer test-token"},
            timeout=15,
        )

    @mock.patch("vikunja_wizard_data.resolve_token")
    @mock.patch("requests.get")
    def test_cmd_labels_output(self, mock_get, mock_token):
        """test_vikunja_wizard_cmd_labels: cmd_labels outputs label list."""
        mock_token.return_value = "test-token"
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": 1, "title": "todo", "color": "#FF0000"},
        ]
        mock_response.headers = {}
        mock_get.return_value = mock_response

        with mock.patch("sys.stdout", new=StringIO()) as fake_out:
            wizard.cmd_labels()

        output = json.loads(fake_out.getvalue())
        self.assertIsInstance(output, list)
        self.assertEqual(output[0]["title"], "todo")

    @mock.patch("vikunja_wizard_data.resolve_token")
    @mock.patch("requests.get")
    def test_cmd_teams_output(self, mock_get, mock_token):
        """test_vikunja_wizard_cmd_teams: cmd_teams outputs team list."""
        mock_token.return_value = "test-token"
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": 1, "name": "Engineering"},
        ]
        mock_response.headers = {}
        mock_get.return_value = mock_response

        with mock.patch("sys.stdout", new=StringIO()) as fake_out:
            wizard.cmd_teams()

        output = json.loads(fake_out.getvalue())
        self.assertIsInstance(output, list)
        self.assertEqual(output[0]["name"], "Engineering")

    @mock.patch("vikunja_wizard_data.resolve_token")
    @mock.patch("requests.get")
    def test_cmd_full_output(self, mock_get, mock_token):
        """test_vikunja_wizard_cmd_full: cmd_full merges projects + teams + labels."""
        mock_token.return_value = "test-token"

        def mock_side_effect(url, **kwargs):
            resp = mock.Mock()
            resp.status_code = 200
            resp.headers = {}
            if "project" in url:
                resp.json.return_value = [
                    {"id": 1, "title": "P1", "team_id": None}
                ]
            elif "team" in url:
                resp.json.return_value = [{"id": 1, "name": "T1"}]
            elif "label" in url:
                resp.json.return_value = [{"id": 1, "title": "L1", "color": "#000"}]
            else:
                resp.status_code = 404
                resp.json.return_value = {"detail": "Not found"}
            return resp

        mock_get.side_effect = mock_side_effect

        with mock.patch("sys.stdout", new=StringIO()) as fake_out:
            wizard.cmd_full()

        output = json.loads(fake_out.getvalue())
        self.assertIsInstance(output, dict)
        self.assertIn("projects", output)
        self.assertIn("teams", output)
        self.assertIn("labels", output)
        self.assertEqual(len(output["projects"]), 1)
        self.assertEqual(len(output["teams"]), 1)
        self.assertEqual(len(output["labels"]), 1)

    def test_resolve_token_from_env(self):
        """test_vikunja_wizard_resolve_token_env: resolves from VIKUNJA_BMS_TOKEN env var."""
        with mock.patch.dict(os.environ, {"VIKUNJA_BMS_TOKEN": "my-token"}):
            token = wizard.resolve_token()
        self.assertEqual(token, "my-token")

    @mock.patch("subprocess.run")
    def test_resolve_token_from_mcp(self, mock_subprocess):
        """test_vikunja_wizard_resolve_token_mcp: falls back to mcp-run.sh."""
        with mock.patch.dict(os.environ, {}, clear=False):
            if "VIKUNJA_BMS_TOKEN" in os.environ:
                del os.environ["VIKUNJA_BMS_TOKEN"]

        mock_result = mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "VIKUNJA_BMS_TOKEN=mcp-token"
        mock_subprocess.return_value = mock_result

        token = wizard.resolve_token()
        self.assertEqual(token, "mcp-token")

    def test_parse_relative_date(self):
        """test_vikunja_wizard_parse_relative_date: re is in __main__ block; patch module."""
        import re as _re
        wizard.re = _re
        self.assertIsNotNone(wizard.parse_relative_date("tomorrow"))
        self.assertIsNotNone(wizard.parse_relative_date("in 3 days"))
        self.assertIsNotNone(wizard.parse_relative_date("next monday"))
        self.assertIsNone(wizard.parse_relative_date("unknown format xyz"))

    def test_load_tenants_from_file(self):
        """test_vikunja_wizard_load_tenants: loads tenants from local file."""
        # TENANTS_FILE already set at module load — patch it
        orig = wizard.TENANTS_FILE
        wizard.TENANTS_FILE = self.tenants_file
        try:
            tenants = wizard.load_tenants()
            self.assertIn("bms", tenants)
            self.assertEqual(tenants["bms"]["base_url"], "http://localhost:3456")
        finally:
            wizard.TENANTS_FILE = orig

    def test_load_tenants_empty_file(self):
        """test_vikunja_wizard_load_tenants_empty: returns empty dict when file missing."""
        # TENANTS_FILE already set at module load — patch it to a nonexistent path
        orig = wizard.TENANTS_FILE
        wizard.TENANTS_FILE = Path("/nonexistent")
        try:
            tenants = wizard.load_tenants()
            self.assertEqual(tenants, {})
        finally:
            wizard.TENANTS_FILE = orig
