"""主题字体（majorFont/minorFont）解析。"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional

from .docx import qn

_LANG_TO_SCRIPT = {
    "zh-CN": "Hans",
    "zh-TW": "Hant",
}


@dataclass
class FontGroup:
    """majorFont 或 minorFont 字体组。"""

    latin: str = ""
    ea: str = ""
    scripts: dict[str, str] = field(default_factory=dict)


class Theme:
    """theme1.xml 的解析结果。"""

    def __init__(self, root: ET.Element):
        self.major = FontGroup()
        self.minor = FontGroup()
        scheme = root.find(".//" + qn(
            "http://schemas.openxmlformats.org/drawingml/2006/main", "fontScheme"))
        if scheme is None:
            return
        for tag, group in (("majorFont", self.major), ("minorFont", self.minor)):
            elem = scheme.find(qn(
                "http://schemas.openxmlformats.org/drawingml/2006/main", tag))
            if elem is not None:
                self._fill(elem, group)

    @staticmethod
    def _fill(elem: ET.Element, group: FontGroup) -> None:
        a = "http://schemas.openxmlformats.org/drawingml/2006/main"
        latin = elem.find(qn(a, "latin"))
        if latin is not None:
            group.latin = latin.get("typeface", "")
        ea = elem.find(qn(a, "ea"))
        if ea is not None:
            group.ea = ea.get("typeface", "")
        for font in elem.findall(qn(a, "font")):
            script = font.get("script")
            typeface = font.get("typeface")
            if script and typeface:
                group.scripts[script] = typeface

    def resolve(
        self, major_or_minor: str, slot: str, lang_east_asia: Optional[str]
    ) -> tuple[Optional[str], Optional[str]]:
        """解析主题字体引用。

        返回 (字体名, None)；无法解析时返回 (None, 错误原因)。
        ascii/hAnsi 取 latin；eastAsia 取 ea，ea 为空时按 lang.eastAsia
        选择脚本项。
        """
        group = self.major if major_or_minor == "major" else self.minor
        if slot in ("ascii", "hAnsi"):
            return (group.latin or None), None if group.latin else "missing-font"
        if group.ea:
            return group.ea, None
        if lang_east_asia is None:
            return None, "unsupported-language"
        script = _LANG_TO_SCRIPT.get(lang_east_asia)
        if script is None:
            return None, "unsupported-language"
        font = group.scripts.get(script)
        if font is None:
            return None, "missing-script-font"
        return font, None
