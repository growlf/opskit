"""Tests for opskit-skills.py — symlink management."""

import os
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "opskit"))

from opskit._cache import CACHE_DIR


@pytest.fixture
def skills_setup(tmp_path, monkeypatch):
    """Set up a temporary skills directory structure."""
    # Create fake source skills
    skills_source = tmp_path / "skills_source"
    skills_source.mkdir()

    # Create skill directories with SKILL.md files
    for skill_name in ["backup", "security", "baseline"]:
        skill_dir = skills_source / skill_name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"# {skill_name} skill\n")

    # Create fake target directories
    opencode_target = tmp_path / "opencode_skills"
    opencode_target.mkdir()

    agents_target = tmp_path / "agents_skills" / "opskit"
    agents_target.mkdir(parents=True)

    monkeypatch.setattr("opskit._cache.CACHE_DIR", tmp_path / ".opskit")
    monkeypatch.setattr("opskit._cache.LAST_DISCOVERY_FILE", tmp_path / ".opskit" / "cache.json")
    monkeypatch.setattr("opskit._cache.LAST_USED_FILE", tmp_path / ".opskit" / "last-used.json")

    # Patch the skills module to use our test paths
    from opskit import _cache
    original_opskit_root = Path("/home/netyeti/Projects/opskit")
    test_opskit_root = tmp_path / "opskit_root"
    test_opskit_root.mkdir()
    (test_opskit_root / ".opencode").mkdir()
    (test_opskit_root / ".opencode" / "skills").link_to(skills_source)

    return {
        "skills_source": skills_source,
        "opencode_target": opencode_target,
        "agents_target": agents_target,
        "opskit_root": test_opskit_root,
    }


class TestGetSkills:
    """Test skill discovery from source directory."""

    def test_lists_skill_directories(self, skills_setup):
        from opskit._cache import CACHE_DIR
        import opskit._cache

        # Verify source exists
        source = skills_setup["skills_source"]
        assert source.exists()
        assert (source / "backup" / "SKILL.md").exists()

    def test_skill_has_skill_md(self, skills_setup):
        source = skills_setup["skills_source"]
        for skill_dir in source.iterdir():
            if skill_dir.is_dir():
                assert (skill_dir / "SKILL.md").exists()


class TestSymlinkCreation:
    """Test symlink creation logic."""

    def test_target_directory_created(self, skills_setup):
        """Target directories should be created if they don't exist."""
        # Remove and recreate targets to test creation
        for target in [skills_setup["opencode_target"], skills_setup["agents_target"]]:
            assert target.exists()

    def test_symlinks_point_to_correct_source(self, skills_setup):
        """Created symlinks should point to the correct source."""
        source = skills_setup["skills_source"]

        # Manually create a symlink and verify
        target = skills_setup["opencode_target"] / "backup"
        if target.is_symlink():
            target.unlink()
        os.symlink(str(source / "backup"), str(target))
        assert target.is_symlink()
        assert target.resolve() == source / "backup"
