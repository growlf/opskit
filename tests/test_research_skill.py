"""The research skill and its /research command must stay real and discoverable.

Two ways this pair degrades silently, and both are worse than having no skill:

- the command survives while the skill it names is renamed or deleted, so the
  agent is told to load a procedure that does not exist and falls back to
  answering from memory — the exact defect the skill exists to prevent;
- the skill's frontmatter drifts off the canonical four fields, so discovery
  stops advertising it and nobody notices, because a missing skill looks
  identical to a skill that was never needed.

The definition-of-done guard already covers AGENTS.md registration for new
files; it only fires on the commit that adds them, so registration is re-checked
here too.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".opencode" / "skills" / "research" / "SKILL.md"
COMMAND = ROOT / ".opencode" / "command" / "research.md"
AGENTS = ROOT / "AGENTS.md"

CANONICAL_FIELDS = ["name", "description", "mode", "triggers"]
MAX_CONTENT_LINES = 60


def _split_frontmatter(path):
    """(field names, frontmatter text, body) for a Markdown file."""
    text = path.read_text()
    lines = text.splitlines()
    assert lines and lines[0].strip() == "---", f"{path}: no frontmatter"
    try:
        end = lines.index("---", 1)
    except ValueError:  # pragma: no cover - malformed file
        raise AssertionError(f"{path}: frontmatter is never closed")
    fields = [
        line.split(":", 1)[0].strip()
        for line in lines[1:end]
        if line and not line.startswith((" ", "\t")) and ":" in line
    ]
    return fields, "\n".join(lines[1:end]), "\n".join(lines[end + 1:])


def test_skill_exists_with_the_canonical_four_fields():
    assert SKILL.is_file(), "the research skill is missing"
    fields, frontmatter, _ = _split_frontmatter(SKILL)
    assert fields == CANONICAL_FIELDS, (
        "skills carry exactly name/description/mode/triggers — a fifth field or "
        f"a reordering breaks discovery; found {fields}"
    )
    assert re.search(r"^name:\s*research\s*$", frontmatter, re.M)
    assert re.search(r"^mode:\s*skill\s*$", frontmatter, re.M)


def test_skill_is_short_enough_to_load_every_time():
    """A skill costs tokens on every matching message; a long one is skipped."""
    _, _, body = _split_frontmatter(SKILL)
    content_lines = [line for line in body.splitlines() if line.strip()]
    assert len(content_lines) <= MAX_CONTENT_LINES, (
        f"{len(content_lines)} content lines exceeds the {MAX_CONTENT_LINES} "
        "ceiling — move procedure detail to docs/ and reference it"
    )


def test_command_loads_the_skill_and_takes_arguments():
    assert COMMAND.is_file(), "the /research command is missing"
    _, frontmatter, body = _split_frontmatter(COMMAND)
    assert re.search(r"^description:\s*\S", frontmatter, re.M), (
        "the command needs a description or it reads as an unlabelled prompt"
    )
    assert "`research`" in body, (
        "the command must name the `research` skill it loads, so renaming the "
        "skill fails here instead of silently degrading to an unsourced answer"
    )
    assert "$ARGUMENTS" in body, "the command must pass the operator's topic through"


def test_skill_is_registered_in_agents_md():
    assert "`research`" in AGENTS.read_text(), (
        "AGENTS.md is the discovery surface agents read first; an unregistered "
        "skill is one nobody loads — bin/definition-of-done-guard.py rejects "
        "this on the commit that adds it"
    )


def test_skill_carries_the_no_guess_rule():
    """The one sentence that makes the pair worth having."""
    _, _, body = _split_frontmatter(SKILL)
    lowered = body.lower()
    assert "guess" in lowered, "the no-guess rule is the point of the skill"
    assert "unverified" in lowered, (
        "the skill must make 'unverified' an acceptable answer, or the agent "
        "has no honest output for a question it cannot source"
    )
