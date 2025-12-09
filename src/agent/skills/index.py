"""
Central index of available skills.
"""

from pathlib import Path
from typing import Dict, List, Optional
from .loader import SkillLoader, SkillMetadata
import logging

logger = logging.getLogger(__name__)


class SkillIndex:
    """
    Maintains an index of all available skills.
    Supports discovery and lookup.
    """
    
    def __init__(self, base_path: Optional[str] = None):
        self._skills: Dict[str, SkillMetadata] = {}
        self._base_path = Path(base_path) if base_path else None
    
    def set_base_path(self, path: str):
        """Set the skills base directory."""
        self._base_path = Path(path)
    
    def discover(self):
        """Scan base path and index all skills."""
        if not self._base_path:
            logger.warning("No base path set for skill discovery")
            return
        
        self._skills.clear()
        skills = SkillLoader.discover(self._base_path)
        
        for skill in skills:
            self._skills[skill.name] = skill
        
        logger.info(f"Indexed {len(self._skills)} skills")
    
    def register(self, skill: SkillMetadata):
        """Manually register a skill."""
        self._skills[skill.name] = skill
    
    def unregister(self, name: str) -> bool:
        """Remove a skill from the index."""
        if name in self._skills:
            del self._skills[name]
            return True
        return False
    
    def get_skill(self, name: str) -> Optional[SkillMetadata]:
        """Get a skill by name."""
        return self._skills.get(name)
    
    def list_skills(self) -> List[SkillMetadata]:
        """List all indexed skills."""
        return list(self._skills.values())
    
    def get_skill_summaries(self) -> List[Dict]:
        """Get summaries for system prompt inclusion."""
        return [
            {"name": s.name, "description": s.description}
            for s in self._skills.values()
        ]
    
    @property
    def base_path(self) -> Optional[Path]:
        return self._base_path


# Global skill index instance
skill_index = SkillIndex()
