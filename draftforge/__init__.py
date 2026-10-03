"""DraftForge DOCX 字体合规检查库。

公开操作：
- inspect(path) -> InspectResult：输出全部有效字体片段与未解析错误。
- validate(path, allowed_fonts) -> ValidateResult：输出全部白名单违规与未解析错误。
"""

from .core import inspect, validate
from .types import (
    FontSegment,
    InspectResult,
    UnresolvedError,
    ValidateResult,
    Violation,
)

__all__ = [
    "inspect",
    "validate",
    "FontSegment",
    "InspectResult",
    "UnresolvedError",
    "ValidateResult",
    "Violation",
]
