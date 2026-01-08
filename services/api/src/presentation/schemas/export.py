"""Export-related schemas."""

from __future__ import annotations

from enum import Enum


class ExportFormat(str, Enum):
    """Supported export formats."""

    CSV = "csv"
    JSON = "json"
