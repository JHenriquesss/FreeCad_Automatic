import json
import os
import tempfile
from dataclasses import replace
from pathlib import Path

from .models import FailureRecord, LoopPhase, LoopState, VALID_TRANSITIONS


_SCHEMA_PATH = Path(__file__).with_name("schema") / "development-loop.schema.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


class Ledger:
    def __init__(self, path, state):
        self.path = Path(path)
        self.state = state
        self._validate(self.state.to_dict())

    @classmethod
    def load(cls, path):
        ledger_path = Path(path)
        document = json.loads(ledger_path.read_text(encoding="utf-8"))
        cls._validate(document)
        return cls(ledger_path, LoopState.from_dict(document))

    def save(self, state=None):
        candidate = self.state if state is None else state
        document = candidate.to_dict()
        self._validate(document)
        serialized = json.dumps(document, indent=2, sort_keys=True) + "\n"
        self._validate(json.loads(serialized))

        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(serialized)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, self.path)
        except BaseException:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
            raise
        self.state = candidate

    def transition(self, expected_phase, next_phase):
        expected = LoopPhase(expected_phase)
        target = LoopPhase(next_phase)
        if self.state.phase is not expected:
            raise ValueError(f"expected phase {expected.value}, got {self.state.phase.value}")
        if target.value not in VALID_TRANSITIONS[expected.value]:
            raise ValueError(f"invalid transition {expected.value} -> {target.value}")
        self.save(replace(self.state, phase=target))

    def record_failure(self, reason, command, artifacts, detail=None):
        if command is not None and (
            isinstance(command, str) or not isinstance(command, (list, tuple))
        ):
            raise ValueError("failure command must be an array or null")
        if isinstance(artifacts, str) or not isinstance(artifacts, (list, tuple)):
            raise ValueError("failure artifacts must be an array")
        failure = FailureRecord(
            reason=reason,
            command=tuple(command) if command is not None else None,
            artifacts=tuple(artifacts),
            detail=detail,
        )
        self.save(replace(self.state, failure=failure))

    @staticmethod
    def _validate(document):
        _validate_schema(document, _SCHEMA)


def _validate_schema(value, schema, location="$"):
    expected_type = schema.get("type")
    if expected_type is not None:
        accepted_types = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(_matches_type(value, type_name) for type_name in accepted_types):
            raise ValueError(f"ledger document does not match schema at {location}: type")

    if "const" in schema and value != schema["const"]:
        raise ValueError(f"ledger document does not match schema at {location}: const")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"ledger document does not match schema at {location}: enum")
    if "minimum" in schema and value < schema["minimum"]:
        raise ValueError(f"ledger document does not match schema at {location}: minimum")
    if "minLength" in schema and len(value) < schema["minLength"]:
        raise ValueError(f"ledger document does not match schema at {location}: minLength")
    if "minItems" in schema and len(value) < schema["minItems"]:
        raise ValueError(f"ledger document does not match schema at {location}: minItems")

    if _matches_type(value, "object"):
        required = schema.get("required", [])
        missing = [name for name in required if name not in value]
        if missing:
            raise ValueError(f"ledger document does not match schema at {location}: required")
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for name, child in value.items():
            child_location = f"{location}.{name}"
            if name in properties:
                _validate_schema(child, properties[name], child_location)
            elif additional is False:
                raise ValueError(f"ledger document does not match schema at {child_location}: additional")
            elif isinstance(additional, dict):
                _validate_schema(child, additional, child_location)

    if _matches_type(value, "array") and "items" in schema:
        for index, child in enumerate(value):
            _validate_schema(child, schema["items"], f"{location}[{index}]")


def _matches_type(value, type_name):
    if type_name == "null":
        return value is None
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "array":
        return isinstance(value, list)
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "boolean":
        return isinstance(value, bool)
    return False
