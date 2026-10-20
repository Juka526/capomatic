"""Strict structured boundaries using the project's existing Pydantic dependency."""
import json
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

Text = Annotated[str, Field(min_length=1)]
SHA = Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')]


class Structured(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    @model_validator(mode='after')
    def unique_lists(self):
        for value in self.__dict__.values():
            if isinstance(value, list) and len(value) != len(set(value)):
                raise ValueError('duplicate structured list items')
        return self


class Task(Structured):
    id: Annotated[str, Field(pattern=r'^[a-z][a-z0-9-]{0,63}$')]
    operation: Literal['research']
    paths: Annotated[list[Text], Field(min_length=1, max_length=4)]
    depends_on: list[Text]
    requires_owner: bool
    instruction: Annotated[str, Field(min_length=1, max_length=4000)]


class Result(Structured):
    task_id: Text
    summary: Text
    changed_paths: list[Text]
    status: Literal['implemented', 'blocked']


class Review(Structured):
    task_id: Text
    snapshot_sha256: SHA
    verdict: Literal['pass', 'revise', 'block']
    findings: list[Text]
    summary: Text


class Packet(Structured):
    id: Text
    manifest: Annotated[dict[str, SHA], Field(min_length=1)]
    candidate_ids: Annotated[list[Text], Field(min_length=1)]
    images: Annotated[list[Text], Field(min_length=1)]
    interpretations: Annotated[dict[str, Text], Field(min_length=1)]
    owner_answer: str | None
    owner_corrections: str | None
    withheld: Annotated[list[Text], Field(min_length=1)]


class Approval(Structured):
    request_id: Text
    packet_sha256: SHA
    owner_identity: Text
    answer: Literal['approve', 'correct', 'reject']
    corrections: str
    candidate_ids: Annotated[list[Text], Field(min_length=1)]
    response_text: Text
    source_response_sha256: SHA


MODELS = {'task': Task, 'result': Result, 'review': Review, 'packet': Packet, 'approval': Approval}


def validate(kind: str, value: object) -> dict:
    """Validate without coercion or unknown fields; emit plain JSON-compatible data."""
    return MODELS[kind].model_validate(value).model_dump()


def load(kind: str, text: str) -> dict:
    """Decode and validate structured agent output."""
    return validate(kind, json.loads(text))
