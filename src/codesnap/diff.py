import difflib

from rich.text import Text


class DiffGenerator:
    """
    Generates diffs between file contents.

    Provides both plain text and rich (colored) diff generation capabilities
    using Python's built-in difflib module and rich text formatting.
    """

    @staticmethod
    def generate_diff(old_content: str, new_content: str) -> str:
        """
        Generate a unified diff between two content strings with dual line numbers.

        Args:
            old_content: The original content to compare
            new_content: The new content to compare against

        Returns:
            Unified diff string showing changes between the two contents
        """
        diff = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile="old",
            tofile="new",
        )
        return "".join(diff)

    @staticmethod
    def generate_diff_rich(old_content: str, new_content: str) -> Text:
        """
        Generate a rich Text diff between two content strings with color formatting.

        Args:
            old_content: The original content to compare
            new_content: The new content to compare against

        Returns:
            Rich Text object with color-coded diff lines
        """
        diff_lines = difflib.unified_diff(
            old_content.splitlines(), new_content.splitlines()
        )

        diff_text = Text()
        for line in diff_lines:
            if line.startswith("+"):
                diff_text.append(line + "\n", style="green")
            elif line.startswith("-"):
                diff_text.append(line + "\n", style="red")
            elif line.startswith("@@"):
                diff_text.append(line, style="cyan")
            else:
                diff_text.append(line + "\n")

        return diff_text
