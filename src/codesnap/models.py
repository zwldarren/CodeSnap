from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    pass


class Prompt(BaseModel):
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=True)


class Checkpoint(BaseModel):
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
        """Get a display name for the checkpoint.

        Returns:
            Prompt content truncated to 50 characters if available,
            otherwise "Checkpoint {id}" format
        """
        if self.prompt and self.prompt.content:
            return self.prompt.content[:50] + (
                "..." if len(self.prompt.content) > 50 else ""
            )
        return f"Checkpoint {self.id}"

    model_config = ConfigDict(use_enum_values=True)


class CodeChange(BaseModel):
    file_path: str
    change_type: str  # "added", "modified", "deleted"
    old_content: str | None = None
    new_content: str | None = None
    diff: Any | None = None


class ExportFormat(str, Enum):
    MARKDOWN = "markdown"
    HTML = "html"
