# Task 2 fix report: direct adapter import cycle

## Scope

- Base commit: `e4a5dac7c87b31db26635623de4cd3069403f3c5`.
- Changed only the allowed builtin loader, galpao adapter, two focused tests,
  and this report.
- `project_loop.py`, the residential spec, and residential production files
  were not modified.

## Root cause and minimal fix

`galpao_adapter` imports `project_loop`; its bootstrap calls
`register_builtin_adapters`, which previously re-imported the partial adapter
before `register_galpao_adapter` existed. The loader now returns only for that
partial module state, without catching unrelated import errors. The completed
adapter registers itself once its definitions are available, preserving the
normal `import project_loop` registration path.

## RED

Command:

```text
python -m pytest tests\\branches\\project_loop\\test_project_loop_generalization.py::test_galpao_adapter_is_directly_importable_in_a_fresh_process -q
```

Output:

```text
F                                                                        [100%]
================================== FAILURES ===================================
________ test_galpao_adapter_is_directly_importable_in_a_fresh_process ________

    def test_galpao_adapter_is_directly_importable_in_a_fresh_process():
        script = r'''
    import sys

    sys.path.insert(0, sys.argv[1])
    import galpao_adapter

    assert callable(galpao_adapter.register_galpao_adapter)
    '''
        completed = subprocess.run(
            [sys.executable, "-c", script, str(ROOT)],
            capture_output=True, text=True,
        )
>       assert completed.returncode == 0, completed.stderr or completed.stdout
E       AssertionError: Traceback (most recent call last):
E           File "<string>", line 5, in <module>
E           File "C:\\Users\\joseh\\OneDrive\\Área de Trabalho\\dev\\FreeCad_Automatic\\framework\\galpao_fw\\galpao_adapter.py", line 9, in <module>
E             from project_loop import (
E           File "C:\\Users\\joseh\\OneDrive\\Área de Trabalho\\dev\\FreeCad_Automatic\\framework\\galpao_fw\\project_loop.py", line 1534, in <module>
E             register_builtin_adapters()
E           File "C:\\Users\\joseh\\OneDrive\\Área de Trabalho\\dev\\FreeCad_Automatic\\framework\\galpao_fw\\builtin_adapters.py", line 5, in register_builtin_adapters
E             from galpao_adapter import register_galpao_adapter
E         ImportError: cannot import name 'register_galpao_adapter' from partially initialized module 'galpao_adapter' (most likely due to a circular import) (C:\\Users\\joseh\\OneDrive\\Área de Trabalho\\dev\\FreeCad_Automatic\\framework\\galpao_fw\\galpao_adapter.py)
E
E       assert 1 == 0
E        +  where 1 = CompletedProcess(args=['C:\\Users\\joseh\\AppData\\Local\\Programs\\Python\\Python312\\python.exe', '-c', '\\nimport sy...rt) (C:\\Users\\joseh\\OneDrive\\Área de Trabalho\\dev\\FreeCad_Automatic\\framework\\galpao_fw\\galpao_adapter.py)\\n').returncode

tests\\branches\\project_loop\\test_project_loop_generalization.py:53: AssertionError
=========================== short test summary info ===========================
FAILED tests/branches/project_loop/test_project_loop_generalization.py::test_galpao_adapter_is_directly_importable_in_a_fresh_process
1 failed in 0.27s
```

## GREEN and focused regressions

```text
python -m pytest tests\\branches\\project_loop\\test_project_loop_generalization.py::test_galpao_adapter_is_directly_importable_in_a_fresh_process -q
.                                                                        [100%]
1 passed in 0.21s
```

```text
python -m pytest tests\\branches\\project_loop\\test_project_loop_adapter_contract.py -q
......                                                                   [100%]
6 passed in 1.30s
```

```text
python -m pytest tests\\trunk\\test_project_loop_golden_journey.py -q
.                                                                        [100%]
1 passed in 3.08s
```

An additional fresh-process check imported `galpao_adapter`, then
`project_loop`, and confirmed `describe_adapters()` includes `galpao`.

## Diff check

`git diff --check` exited with code 0. It emitted only existing CRLF conversion
warnings from the dirty worktree; it reported no whitespace errors.
