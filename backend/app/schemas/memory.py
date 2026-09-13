"""
Validation Schemas for Memory Agent Classification and Storage.
"""

try:
    from pydantic import BaseModel
    from typing import Literal, Optional

    class MemoryClassificationOutput(BaseModel):
        operation: Literal["store", "retrieve", "none"]
        classification: Literal["TEMPORARY_CONTEXT", "LONG_TERM_PREFERENCE", "IMPORTANT_INSTRUCTION", "IRRELEVANT"]
        content: str
        reason: Optional[str] = None

except ImportError:
    from dataclasses import dataclass
    from typing import Optional

    @dataclass
    class MemoryClassificationOutput:
        operation: str
        classification: str
        content: str
        reason: Optional[str] = None
