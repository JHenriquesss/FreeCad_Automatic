import json
import subprocess
from pathlib import Path

import pytest

from tools.loops.config import load_config
from tools.loops.worktrees import WorktreeManager


def git(*args, cwd):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def make_repository(tmp_path):
    repository = tmp_path / "project"
    repository.mkdir()
    git("init", "-b", "main", cwd=repository)
    git("config", "user.name", "Task 2 Test", cwd=repository)
    git("config", "user.email", "task2@example.test", cwd=repository)
    (repository / ".gitignore").write_text(".loop-runtime/\n", encoding="utf-8")
    (repository / "tracked.txt").write_text("initial\n", encoding="utf-8")
    git("add", ".gitignore", "tracked.txt", cwd=repository)
    git("commit", "-m", "initial", cwd=repository)
    return repository, git("rev-parse", "HEAD", cwd=repository)


def test_load_config_uses_project_root_for_relative_paths(tmp_path):
    repository = tmp_path / "project"
    repository.mkdir()
    config_path = repository / "loop.json"
    config_path.write_text(json.dumps({"runtime_dir": "runtime"}), encoding="utf-8")

    config = load_config("loop.json", repository)

    assert Path(config.project_root) == repository.resolve()
    assert Path(config.runtime_dir) == (repository / "runtime").resolve()
    assert config.mode == "supervised"
    assert config.executor == "codex"
    assert config.max_iterations == 1
    assert config.max_attempts_per_phase == 3
    assert config.command_timeout_seconds == 900
    assert config.build_timeout_seconds == 1800
    assert config.retry_blocked is False


def test_load_config_rejects_non_boolean_retry_blocked(tmp_path):
    config_path = tmp_path / "loop.json"
    config_path.write_text(json.dumps({"retry_blocked": "yes"}), encoding="utf-8")

    with pytest.raises(ValueError, match="retry_blocked"):
        load_config(config_path, tmp_path)


def test_worktree_creation_is_based_on_exact_commit(tmp_path):
    repository, base_commit = make_repository(tmp_path)
    manager = WorktreeManager(repository, repository / ".loop-runtime")
    root_before = git("status", "--porcelain", cwd=repository)

    (repository / "tracked.txt").write_text("root-only change\n", encoding="utf-8")
    git("add", "tracked.txt", cwd=repository)
    git("commit", "-m", "root change", cwd=repository)
    root_head = git("rev-parse", "HEAD", cwd=repository)

    worktree = Path(manager.create("loop-1", base_commit))

    assert git("rev-parse", "HEAD", cwd=worktree) == base_commit
    assert (worktree / "tracked.txt").read_text(encoding="utf-8") == "initial\n"
    assert git("rev-parse", "HEAD", cwd=repository) == root_head
    assert git("status", "--porcelain", cwd=repository) == root_before

    manager.remove("loop-1")


def test_root_head_change_raises_external_change(tmp_path):
    repository, base_commit = make_repository(tmp_path)
    manager = WorktreeManager(repository, repository / ".loop-runtime")

    (repository / "tracked.txt").write_text("external change\n", encoding="utf-8")
    git("add", "tracked.txt", cwd=repository)
    git("commit", "-m", "external change", cwd=repository)

    with pytest.raises(RuntimeError, match="external change"):
        manager.assert_base_unchanged(base_commit)


def test_assert_base_unchanged_accepts_abbreviated_commit(tmp_path):
    repository, base_commit = make_repository(tmp_path)
    manager = WorktreeManager(repository, repository / ".loop-runtime")

    manager.assert_base_unchanged(base_commit[:8])


def test_remove_rejects_path_outside_runtime(tmp_path):
    repository, base_commit = make_repository(tmp_path)
    manager = WorktreeManager(repository, repository / ".loop-runtime")
    outside = tmp_path / "outside"
    git("worktree", "add", "-b", "outside", str(outside), base_commit, cwd=repository)

    with pytest.raises(ValueError, match="runtime"):
        manager.remove("outside")

    git("worktree", "remove", "--force", str(outside), cwd=repository)


@pytest.mark.parametrize("loop_id", ["", ".", "..", "../escape", r"..\escape", "a/b", r"a\b", "bad name"])
def test_invalid_loop_id_is_rejected(tmp_path, loop_id):
    repository, base_commit = make_repository(tmp_path)
    manager = WorktreeManager(repository, repository / ".loop-runtime")

    with pytest.raises(ValueError, match="loop_id"):
        manager.create(loop_id, base_commit)


@pytest.mark.parametrize("loop_id", ["a..b", "a."])
def test_git_invalid_loop_id_is_rejected_before_runtime_creation(tmp_path, loop_id):
    repository, base_commit = make_repository(tmp_path)
    manager = WorktreeManager(repository, repository / ".loop-runtime")

    with pytest.raises(ValueError, match="loop_id"):
        manager.create(loop_id, base_commit)

    assert not (repository / ".loop-runtime").exists()


def test_git_lock_suffix_loop_id_is_rejected_before_runtime_creation(tmp_path):
    repository, base_commit = make_repository(tmp_path)
    manager = WorktreeManager(repository, repository / ".loop-runtime")

    with pytest.raises(ValueError, match="loop_id"):
        manager.create("a.lock", base_commit)

    assert not (repository / ".loop-runtime").exists()
    assert not (repository / ".loop-runtime" / "worktrees").exists()
