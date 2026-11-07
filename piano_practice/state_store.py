"""Single-user POSIX JSON state writer with cooperative locking and crash-safe replace.

This is an integrity boundary for cooperating writers, not access control:
the caller and other tools must respect the same lock file.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import tempfile
from typing import Callable

try:
    import fcntl
except ImportError:
    fcntl = None


def transact(path: str | Path, update: Callable[[dict], tuple[dict | None, dict]]) -> dict:
    """Read current state under lock; persist only a validated changed copy.

    update returns (new_state_or_None, result). None represents an idempotent
    no-op. The caller checks state revision, digests and invariants under lock.
    """
    if fcntl is None:
        raise RuntimeError("state updates require POSIX fcntl locking (Linux/macOS)")
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise ValueError("state must be an existing regular non-symlink file")
    parent = target.parent
    lock_path = target.with_name(target.name + ".lock")
    if lock_path.is_symlink():
        raise ValueError("state lock path must not be a symlink")
    old_umask = os.umask(0o077)
    try:
        # O_NOFOLLOW where available prevents a symlink race for the lock itself.
        flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
        lock_fd = os.open(lock_path, flags, 0o600)
    finally:
        os.umask(old_umask)
    try:
        with os.fdopen(lock_fd, "r+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            if target.is_symlink() or not target.is_file():
                raise ValueError("state file changed during approval")
            current_stat = target.stat()
            if not stat.S_ISREG(current_stat.st_mode) or current_stat.st_nlink != 1:
                raise ValueError("state requires a regular, single-link file")
            # Avoid writing through a readable link in a sensitive directory.
            with open(target, encoding="utf-8") as stream:
                state = json.load(stream)
            new_state, result = update(state)
            if new_state is None:
                return result
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                        dir=parent, prefix=".piano-state-", suffix=".tmp",
                        delete=False) as output:
                    temp_path = Path(output.name)
                    json.dump(new_state, output, sort_keys=True, indent=2)
                    output.write("\n")
                    output.flush()
                    os.fsync(output.fileno())
                os.chmod(temp_path, 0o600)
                # An unrelated editor is outside our transaction contract.
                now = target.stat()
                if target.is_symlink() or (now.st_ino, now.st_dev) != (current_stat.st_ino, current_stat.st_dev):
                    raise ValueError("state file changed during approval")
                os.replace(temp_path, target)
                temp_path = None
                directory_fd = os.open(parent, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            finally:
                if temp_path is not None:
                    temp_path.unlink(missing_ok=True)
            return result
    finally:
        pass
