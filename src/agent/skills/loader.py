"""
Parses SKILL.md files to extract skill metadata and documentation.
"""

import frontmatter
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class SkillMetadata:
    """Parsed skill information."""
    name: str
    description: str
    path: Path
    documentation: str  # Full SKILL.md content
    scripts_path: Optional[Path] = None
    
    @property
    def has_scripts(self) -> bool:
        return self.scripts_path is not None and self.scripts_path.exists()


class SkillLoader:
    """Loads and parses SKILL.md files."""
    
    @staticmethod
    def load(skill_path: Path) -> Optional[SkillMetadata]:
        """
        Load a skill from a directory.
        
        Args:
            skill_path: Path to skill directory containing SKILL.md
        
        Returns:
            SkillMetadata or None if invalid
        """
        skill_md_path = skill_path / "SKILL.md"
        
        if not skill_md_path.exists():
            logger.warning(f"No SKILL.md found in {skill_path}")
            return None
        
        try:
            # Parse frontmatter and content
            with open(skill_md_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            # Extract required fields
            name = post.get('name')
            if not name:
                # Fallback to directory name
                name = skill_path.name
            
            description = post.get('description', f"Skill: {name}")
            
            # Full documentation (frontmatter + content)
            full_doc = skill_md_path.read_text(encoding='utf-8')
            
            # Check for scripts directory
            scripts_path = skill_path / "scripts"
            if not scripts_path.exists():
                scripts_path = None
            
            return SkillMetadata(
                name=name,
                description=description,
                path=skill_path,
                documentation=full_doc,
                scripts_path=scripts_path
            )
        
        except Exception as e:
            logger.error(f"Failed to load skill from {skill_path}: {e}")
            return None
    
    @staticmethod
    def discover(base_path: Path) -> List[SkillMetadata]:
        """
        Discover all skills in a directory.
        
        Args:
            base_path: Root directory to scan for skills
        
        Returns:
            List of discovered skills
        """
        skills = []
        
        if not base_path.exists():
            logger.warning(f"Skills base path does not exist: {base_path}")
            return skills
        
        # Each subdirectory is a potential skill
        for item in base_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                skill = SkillLoader.load(item)
                if skill:
                    skills.append(skill)
                    logger.info(f"Discovered skill: {skill.name}")
        
        return skills
