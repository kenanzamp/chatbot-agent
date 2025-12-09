"""Tests for the skill system."""

import pytest
from pathlib import Path
import tempfile
from agent.skills.loader import SkillLoader
from agent.skills.index import SkillIndex


def test_skill_loading(tmp_path):
    """Test that skills can be loaded from SKILL.md files."""
    # Create test skill
    skill_dir = tmp_path / "test_skill"
    skill_dir.mkdir()
    
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: test_skill
description: A test skill for testing
---

# Test Skill

This is a test skill.
""")
    
    skill = SkillLoader.load(skill_dir)
    assert skill is not None
    assert skill.name == "test_skill"
    assert "A test skill for testing" in skill.description


def test_skill_discovery(tmp_path):
    """Test that skills are discovered in a directory."""
    # Create multiple skills
    for i in range(3):
        skill_dir = tmp_path / f"skill_{i}"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"""---
name: skill_{i}
description: Test skill {i}
---

# Skill {i}
""")
    
    skills = SkillLoader.discover(tmp_path)
    assert len(skills) == 3


def test_skill_index():
    """Test the skill index."""
    index = SkillIndex()
    
    # Initially empty
    assert len(index.list_skills()) == 0
    
    # Get non-existent skill
    assert index.get_skill("nonexistent") is None


def test_skill_without_frontmatter(tmp_path):
    """Test loading skill without proper frontmatter."""
    skill_dir = tmp_path / "no_frontmatter"
    skill_dir.mkdir()
    
    # SKILL.md without frontmatter
    (skill_dir / "SKILL.md").write_text("""
# A Skill Without Frontmatter

Just content here.
""")
    
    skill = SkillLoader.load(skill_dir)
    # Should still load, using directory name as skill name
    assert skill is not None
    assert skill.name == "no_frontmatter"
