import os
import re
import subprocess
from pathlib import Path


class ExternalChangeError(RuntimeError):
    pass


class WorktreeManager:
    def __init__(self, project_root, runtime_dir=None):
        if runtime_dir is None:
            config = project_root
            project_root = config.project_root
            runtime_dir = config.runtime_dir
        self.project_root = Path(project_root).expanduser().resolve()
        self.runtime_dir = Path(runtime_dir).expanduser()
        if not self.runtime_dir.is_absolute():
            self.runtime_dir = self.project_root / self.runtime_dir
        self.runtime_dir = self.runtime_dir.resolve()
        self.worktrees_dir = (self.runtime_dir / "worktrees").resolve()

    @staticmethod
    def _validate_loop_id(loop_id):
        if (
            not isinstance(loop_id, str)
            or not loop_id
            or loop_id in {".", ".."}
            or "/" in loop_id
            or "\\" in loop_id
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", loop_id) is None
        ):
            raise ValueError("loop_id must be a safe path component")

    def _worktree_path(self, loop_id):
        self._validate_loop_id(loop_id)
        candidate = (self.worktrees_dir / loop_id).resolve()
        try:
            candidate.relative_to(self.worktrees_dir)
        except ValueError as error:
            raise ValueError("worktree path is outside runtime") from error
        return candidate

    def _git(self, *args):
        return subprocess.run(
            ["git", *args],
            cwd=self.project_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def create(self, loop_id, base_commit):
        worktree_path = self._worktree_path(loop_id)
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)
        self._git(
            "worktree",
            "add",
            "-b",
            f"loop/{loop_id}",
            str(worktree_path),
            base_commit,
        )
        return str(worktree_path)

    def assert_base_unchanged(self, base_commit):
        current_head = self._git("rev-parse", "HEAD")
        if current_head != base_commit:
            raise ExternalChangeError(
                f"external change: project root HEAD is {current_head}, expected {base_commit}"
            )

    def _registered_worktrees(self):
        output = self._git("worktree", "list", "--porcelain")
        return {
            Path(line.removeprefix("worktree ")).resolve()
            for line in output.splitlines()
            if line.startswith("worktree ")
        }

    def remove(self, loop_id):
        worktree_path = self._worktree_path(loop_id)
        registered = {
            os.path.normcase(str(path)) for path in self._registered_worktrees()
        }
        if os.path.normcase(str(worktree_path)) not in registered:
            raise ValueError("worktree is not registered inside runtime")
        self._git("worktree", "remove", str(worktree_path))
