"""DraftForge 字体合规检查的数据类型定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class FontSegment:
    """一段连续可见文字及其解析出的有效字体。

    part: 来源部件，如 "document"、"header1"、"footer2"。
    text: 该片段的文字内容。
    slot: 字体槽位，"ascii" / "eastAsia" / "hAnsi"。
    font: 解析出的字体名称；无法解析时为 None。
    """

    part: str
    text: str
    slot: str
    font: Optional[str]


@dataclass(frozen=True)
class UnresolvedError:
    """某个可见字符无法解析出有效字体的错误。

    reason 取值：
    - "missing-font": 所有来源均未指定该槽位字体。
    - "unsupported-language": lang.eastAsia 不受支持。
    - "missing-script-font": 主题字体组缺少对应脚本项。
    """

    part: str
    text: str
    slot: str
    reason: str


@dataclass(frozen=True)
class Violation:
    """白名单违规：可见字符使用了不在允许列表中的字体。"""

    part: str
    text: str
    slot: str
    font: str


@dataclass
class InspectResult:
    """inspect() 的返回值。"""

    segments: list[FontSegment] = field(default_factory=list)
    errors: list[UnresolvedError] = field(default_factory=list)


@dataclass
class ValidateResult:
    """validate() 的返回值。"""

    violations: list[Violation] = field(default_factory=list)
    errors: list[UnresolvedError] = field(default_factory=list)
