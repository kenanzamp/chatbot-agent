"""
Secure command execution for skills.
"""

import asyncio
import shlex
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Result of command execution."""
    success: bool
    stdout: str
    stderr: str
    return_code: int
    error: Optional[str] = None


class SkillCommandExecutor:
    """
    Executes shell commands for skills with security controls.
    """
    
    def __init__(
        self,
        base_path: Path,
        allowed_prefixes: List[str],
        timeout: int = 60,
        sandbox: bool = False
    ):
        self.base_path = base_path
        self.allowed_prefixes = allowed_prefixes
        self.timeout = timeout
        self.sandbox = sandbox  # Future: container/sandbox execution
    
    def _validate_command(self, command: str) -> tuple[bool, str]:
        """
        Validate command against security rules.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not command or not command.strip():
            return False, "Empty command"
        
        # Check if command starts with allowed prefix
        try:
            parts = shlex.split(command)
        except ValueError as e:
            return False, f"Invalid command format: {e}"
            
        if not parts:
            return False, "Invalid command format"
        
        cmd_prefix = parts[0].lower()
        
        # Allow full paths to python
        if '/' in cmd_prefix:
            cmd_prefix = cmd_prefix.split('/')[-1]
        
        allowed = any(cmd_prefix.startswith(prefix.lower()) for prefix in self.allowed_prefixes)
        
        if not allowed:
            return False, f"Command '{parts[0]}' not allowed. Allowed: {', '.join(self.allowed_prefixes)}"
        
        # Check for dangerous patterns
        dangerous_patterns = [
            '&&', '||', ';', '|',  # Command chaining
            '`', '$(',             # Command substitution
            'rm -rf', 'rm -fr',    # Dangerous operations
            '/etc/', '/root/',     # Sensitive paths
        ]
        
        for pattern in dangerous_patterns:
            if pattern in command:
                # More nuanced check - only block if pattern is part of shell syntax
                if pattern in ('&&', '||', ';', '|', '`', '$('):
                    return False, f"Shell operators not allowed: {pattern}"
        
        return True, ""
    
    async def execute(
        self,
        command: str,
        working_dir: Optional[str] = None
    ) -> CommandResult:
        """
        Execute a command securely.
        
        Args:
            command: Shell command to execute
            working_dir: Optional subdirectory within base_path
        
        Returns:
            CommandResult with output and status
        """
        # Validate command
        is_valid, error = self._validate_command(command)
        if not is_valid:
            return CommandResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                error=error
            )
        
        # Determine working directory
        cwd = self.base_path
        if working_dir:
            cwd = self.base_path / working_dir
            if not cwd.exists():
                return CommandResult(
                    success=False,
                    stdout="",
                    stderr="",
                    return_code=-1,
                    error=f"Working directory not found: {working_dir}"
                )
        
        try:
            logger.debug(f"Executing command: {command} in {cwd}")
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(cwd)
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return CommandResult(
                    success=False,
                    stdout="",
                    stderr="",
                    return_code=-1,
                    error=f"Command timed out after {self.timeout} seconds"
                )
            
            stdout_str = stdout.decode('utf-8', errors='replace').strip()
            stderr_str = stderr.decode('utf-8', errors='replace').strip()
            
            success = process.returncode == 0
            
            if not success:
                logger.warning(f"Command failed with code {process.returncode}: {stderr_str}")
            
            return CommandResult(
                success=success,
                stdout=stdout_str,
                stderr=stderr_str,
                return_code=process.returncode
            )
        
        except Exception as e:
            logger.exception(f"Command execution error: {e}")
            return CommandResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                error=str(e)
            )
