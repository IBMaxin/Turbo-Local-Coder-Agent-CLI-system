from __future__ import annotations

import logging
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
import re

# Safe read-only commands
WHITELIST: set[str] = {
    "python", "python3", "pytest", "pip", "pip3",
    "ls", "cat", "echo", "pwd", "which", "type",
    "mkdir", "touch", "rm", "git", "grep", "find", "wc",
    "head", "tail", "diff", "tree", "file",
    "black", "ruff", "mypy", "flake8",  # Linters
    "true", "false", "sleep", "date",  # Testing commands
}

# Dangerous patterns that should never be allowed
DANGEROUS_PATTERNS = [
    r'-rf\s*/$',  # rm -rf /
    r'-rf\s*/etc',  # rm -rf /etc
    r'-rf\s*/usr',  # rm -rf /usr
    r'-rf\s*/var',  # rm -rf /var
    r'-rf\s*/home',  # rm -rf /home
    r'-rf\s*/root',  # rm -rf /root
    r'rm\s+-[^\s]*f[^\s]*\s*/$',  # rm with force and root
    r'rm\s+-[^\s]*f[^\s]*\s*/etc',  # rm with force and /etc
    r'rm\s+-[^\s]*f[^\s]*\s*/usr',  # rm with force and /usr
    r'dd\s+.*of=/dev/',  # dd to device
    r'mkfs',  # filesystem formatting
    r'fdisk',
    r'parted',
    r'>/dev/sd',  # writing to disk devices
    r'curl.*\|.*sh',  # curl piped to shell
    r'wget.*\|.*sh',  # wget piped to shell
    r'&&\s*rm',  # chained rm commands
    r';\s*rm',  # semicolon rm
    r'\|\s*rm',  # piped rm
]

# Commands that should be blocked entirely
BLOCKLIST: set[str] = {
    "sudo", "su", "doas",
    "curl", "wget", "nc", "netcat",
    "ssh", "scp", "ftp", "telnet",
    "nmap", "masscan", "nikto",
    "chmod", "chown", "chgrp",
    "systemctl", "service", "reboot", "shutdown",
    "iptables", "ufw", "firewall-cmd",
}


@dataclass
class ShellResult:
    ok: bool
    stdout: str
    stderr: str
    code: int


def _allowed(cmd: str) -> bool:
    """Check if command is safe to execute.
    
    Returns:
        True if command is safe, False otherwise
    """
    if not cmd or not cmd.strip():
        return False
    
    # Check for dangerous patterns first
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return False
    
    # Parse command
    try:
        parts = shlex.split(cmd)
    except ValueError:
        # Malformed command
        return False
    
    if not parts:
        return False
    
    base_command = parts[0]
    
    # Check blocklist
    if base_command in BLOCKLIST:
        return False
    
    # Check whitelist
    if base_command not in WHITELIST:
        return False
    
    # Special validation for rm command
    if base_command == "rm":
        return _validate_rm(parts)
    
    # Special validation for git command
    if base_command == "git":
        return _validate_git(parts)
    
    return True


def _validate_rm(parts: list[str]) -> bool:
    """Validate rm command for safety.
    
    Blocks:
    - rm with -rf and / or system paths
    - rm -rf without specific path
    - rm on /dev, /sys, /proc, /boot, /etc

    Allows:
    - /tmp and ./tmp (for testing purposes)
    - Other user-space paths
    """
    if len(parts) < 2:
        # rm with no args is safe (will error)
        return True
    
    # Check for dangerous flags
    has_recursive = False
    has_force = False
    
    paths = []
    for i, part in enumerate(parts[1:], 1):
        if part.startswith('-'):
            if 'r' in part or 'R' in part:
                has_recursive = True
            if 'f' in part:
                has_force = True
        else:
            paths.append(part)
    
    # Block rm -rf with no path or dangerous paths
    if has_recursive and has_force:
        if not paths:
            return False  # rm -rf with no path

        for path in paths:
            # Normalize path
            normalized = path.replace("\\", "/")

            # Allow relative paths (user-controlled)
            if not normalized.startswith('/'):
                continue

            # For absolute paths, check for dangerous locations
            # Allow /tmp paths explicitly (for testing)
            if normalized == '/tmp' or normalized.startswith('/tmp/'):
                continue

            # Block system directories
            dangerous_paths = ['/home', '/root', '/usr', '/var', '/etc',
                             '/boot', '/dev', '/sys', '/proc']

            # Block root itself
            if normalized == '/':
                return False

            # Block if it starts with a dangerous path
            for dp in dangerous_paths:
                if normalized == dp or normalized.startswith(dp + '/'):
                    return False

    return True


def _validate_git(parts: list[str]) -> bool:
    """Validate git command for safety.
    
    Only allow safe git operations.
    """
    if len(parts) < 2:
        return True  # git with no args is safe
    
    # Allow read-only git operations
    safe_git_commands = {
        'status', 'log', 'diff', 'show', 'branch', 'tag',
        'ls-files', 'ls-tree', 'config', 'remote', 'fetch',
        'add', 'commit', 'push', 'pull', 'checkout', 'clone',
        'init', 'stash', 'reset', 'rebase', 'merge'
    }
    
    git_subcommand = parts[1]
    return git_subcommand in safe_git_commands


def shell_run(cmd: str, timeout_s: int = 60) -> ShellResult:
    """Run a safe command with timeout.
    
    Args:
        cmd: Command to execute
        timeout_s: Timeout in seconds
    
    Returns:
        ShellResult with execution details
    """
    if not _allowed(cmd):
        return ShellResult(False, "", f"blocked: {cmd}", 126)
    
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return ShellResult(
            proc.returncode == 0,
            proc.stdout.strip(),
            proc.stderr.strip(),
            proc.returncode,
        )
    except subprocess.TimeoutExpired as exc:
        logger = logging.getLogger(__name__)
        stdout = exc.stdout
        if isinstance(stdout, memoryview):
            stdout = stdout.tobytes().decode('utf-8', errors='replace')
        elif isinstance(stdout, (bytes, bytearray)):
            stdout = stdout.decode('utf-8', errors='replace')
        elif stdout is None:
            stdout = ""
        logger.warning(f"Timeout running command: {cmd} (timeout={timeout_s}s)")
        logger.info(f"Partial stdout: {stdout[:120] if stdout else '<empty>'}")
        return ShellResult(False, stdout or "", "timeout", 124)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error running command '{cmd}': {e}")
        return ShellResult(False, "", str(e), 1)
