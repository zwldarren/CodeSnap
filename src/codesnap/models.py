from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Prompt(BaseModel):
    """Model for storing user prompts with metadata."""

    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class Checkpoint(BaseModel):
    """Model for storing code checkpoints."""

    id: int
    description: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)
    prompt: Prompt | None = None
    tags: list[str] = Field(default_factory=list)
    file_snapshots: dict[str, str] = Field(default_factory=dict)
    restored_from: int | None = None
    restore_timestamp: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def name(self) -> str:
        """Use prompt content as name."""
        if self.prompt and self.prompt.content:
            return self.prompt.content[:50] + (
                "..." if len(self.prompt.content) > 50 else ""
            )
        return f"Checkpoint {self.id}"

    class Config:
        use_enum_values = True


class CodeChange(BaseModel):
    """Model for storing code changes between checkpoints."""

    file_path: str
    change_type: str  # "added", "modified", "deleted"
    old_content: str | None = None
    new_content: str | None = None
    diff: Any | None = None


class ExportFormat(str, Enum):
    """Supported export formats."""

    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
