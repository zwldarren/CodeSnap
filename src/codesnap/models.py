from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class PromptType(str, Enum):
    """Types of prompts that can be recorded."""

    CODE_GENERATION = "code_generation"
    CODE_MODIFICATION = "code_modification"
    DEBUGGING = "debugging"
    EXPLANATION = "explanation"
    REFACTORING = "refactoring"
    OTHER = "other"


class CheckpointStatus(str, Enum):
    """Status of a checkpoint."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class Prompt(BaseModel):
    """Model for storing user prompts with metadata."""

    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    prompt_type: PromptType = PromptType.OTHER
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class Checkpoint(BaseModel):
    """Model for storing code checkpoints."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)
    prompt: Prompt | None = None
    status: CheckpointStatus = CheckpointStatus.ACTIVE
    tags: list[str] = Field(default_factory=list)
    file_snapshots: dict[str, str] = Field(default_factory=dict)
    branch_id: str | None = None
    restored_from: str | None = None
    restore_timestamp: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class CodeChange(BaseModel):
    """Model for storing code changes between checkpoints."""

    file_path: str
    change_type: str  # "added", "modified", "deleted"
    old_content: str | None = None
    new_content: str | None = None
    diff: Any | None = None


class BranchStatus(str, Enum):
    """Status of a branch."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class Branch(BaseModel):
    """Model for storing branch information."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str = ""
    created_from: str | None = None  # checkpoint_id this branch was created from
    created_at: datetime = Field(default_factory=datetime.now)
    status: BranchStatus = BranchStatus.ACTIVE
    current_checkpoint_id: str | None = None  # Current checkpoint on this branch
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class ExportFormat(str, Enum):
    """Supported export formats."""

    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
