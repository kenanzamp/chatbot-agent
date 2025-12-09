"""
Core built-in tools for agent operation.
These tools enable skill reading and command execution.
"""

from ..registry import tool
from ...skills.index import skill_index
from ...skills.executor import SkillCommandExecutor
from typing import Optional
import json


# Skill command executor instance (initialized in main.py)
_command_executor: Optional[SkillCommandExecutor] = None


def set_command_executor(executor: SkillCommandExecutor):
    """Set the command executor instance (called during startup)."""
    global _command_executor
    _command_executor = executor


@tool(
    name="get_current_time",
    description="Get the current date and time. Use this when the user asks what time it is or needs the current date.",
    timeout=5.0,
    tags=["utility"]
)
def get_current_time() -> str:
    """
    Get the current date and time.
    
    Returns:
        Current datetime as a formatted string
    """
    from datetime import datetime
    now = datetime.now()
    return now.strftime("%I:%M %p on %A, %B %d, %Y")


@tool(
    name="list_skills",
    description="List all available skills with their descriptions. Use this to discover what capabilities are available before attempting a task.",
    timeout=5.0,
    tags=["system", "discovery"]
)
def list_skills() -> str:
    """
    List all available skills.
    
    Returns:
        JSON list of skills with name and description
    """
    skills = skill_index.list_skills()
    return json.dumps([
        {"name": s.name, "description": s.description}
        for s in skills
    ], indent=2)


@tool(
    name="read_skill",
    description="Read the documentation for a specific skill. This returns the SKILL.md content which explains how to use the skill, including command formats and examples. ALWAYS read a skill's documentation before using it.",
    timeout=10.0,
    tags=["system", "discovery"]
)
def read_skill(skill_name: str) -> str:
    """
    Read a skill's documentation.
    
    Args:
        skill_name: Name of the skill to read (e.g., "calculator")
    
    Returns:
        The full SKILL.md content for the skill
    """
    skill = skill_index.get_skill(skill_name)
    if not skill:
        available = [s.name for s in skill_index.list_skills()]
        return f"Skill '{skill_name}' not found. Available skills: {', '.join(available) if available else 'none'}"
    
    return skill.documentation


@tool(
    name="execute_command",
    description="Execute a shell command. Use this to run skill scripts after reading the skill documentation. The command will be executed in the skills directory.",
    timeout=60.0,
    tags=["system", "execution"]
)
async def execute_command(command: str, working_dir: Optional[str] = None) -> str:
    """
    Execute a shell command.
    
    Args:
        command: The shell command to execute (e.g., "python3 scripts/calc.py calc add 5 3")
        working_dir: Optional working directory relative to skills base path
    
    Returns:
        Command output (stdout) or error message
    """
    if _command_executor is None:
        return "Error: Command executor not initialized"
    
    result = await _command_executor.execute(command, working_dir=working_dir)
    
    if result.success:
        return result.stdout or "Command completed successfully (no output)"
    else:
        error_msg = result.stderr or result.error or "Unknown error"
        return f"Command failed: {error_msg}"
