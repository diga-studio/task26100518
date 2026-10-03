"""DraftForge 数据模型定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FontSegment:
    """一段具有相同有效字体（或相同未解析错误）的连续可见文字。"""

    text: str
    font: Optional[str] = None
    error: Optional[str] = None
    part: str = "document"


@dataclass
class Violation:
    """一条字体合规违规记录。"""

    text: str
    font: Optional[str]
    reason: str
    part: str = "document"


@dataclass
class RunProperties:
    """某一层的 run 属性快照；缺失的属性保持 None 以便继续向低层查找。"""

    ascii_font: Optional[str] = None
    ascii_theme: Optional[str] = None
    hansi_font: Optional[str] = None
    hansi_theme: Optional[str] = None
    eastasia_font: Optional[str] = None
    eastasia_theme: Optional[str] = None
    lang_eastasia: Optional[str] = None
    vanish: Optional[bool] = None


@dataclass
class ThemeFonts:
    """主题字体方案。"""

    major_latin: str = ""
    major_ea: str = ""
    major_scripts: dict = field(default_factory=dict)
    minor_latin: str = ""
    minor_ea: str = ""
    minor_scripts: dict = field(default_factory=dict)
