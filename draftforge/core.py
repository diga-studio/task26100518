"""文档遍历、run 分派与公开 API 实现。"""

from __future__ import annotations

import posixpath
import xml.etree.ElementTree as ET
from typing import Iterable, Optional

from .docx import DocxPackage, w
from .styles import RunProps, StyleSheet
from .theme import Theme
from .types import FontSegment, InspectResult, UnresolvedError, ValidateResult, Violation

_EXCLUDED_CONTAINERS = {w("del"), w("moveFrom")}


def _slot_of(ch: str) -> str:
    code = ord(ch)
    if code < 0x80:
        return "ascii"
    if 0x4E00 <= code <= 0x9FFF:
        return "eastAsia"
    return "hAnsi"


def _first(layers: list[RunProps], attr: str):
    for layer in layers:
        value = getattr(layer, attr)
        if value is not None:
            return value
    return None


class _Checker:
    def __init__(self, path: str):
        self._pkg = DocxPackage(path)
        self.styles: Optional[StyleSheet] = None
        self.theme: Optional[Theme] = None
        self.result = InspectResult()

    def run(self) -> InspectResult:
        with self._pkg:
            self.styles = StyleSheet(self._pkg.read_xml("word/styles.xml"))
            theme_name = self._theme_part()
            self.theme = Theme(self._pkg.read_xml(theme_name)) if theme_name else Theme(
                ET.Element("empty"))
            parts = ["word/document.xml"]
            parts.extend(self._referenced_header_footers())
            for part in parts:
                root = self._pkg.read_xml(part)
                self._walk_part(root, self._part_label(part))
        return self.result

    def _theme_part(self) -> Optional[str]:
        rels = self._pkg.read_rels("word/document.xml")
        for target in rels.values():
            if posixpath.basename(target).startswith("theme"):
                return target
        return None

    def _referenced_header_footers(self) -> list[str]:
        """任一 sectPr 通过关系引用的页眉页脚。"""
        rels = self._pkg.read_rels("word/document.xml")
        root = self._pkg.read_xml("word/document.xml")
        found: set[str] = set()
        for sect in root.iter(w("sectPr")):
            for ref in list(sect.iter(w("headerReference"))) + list(
                sect.iter(w("footerReference"))
            ):
                rid = ref.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
                if rid and rid in rels and self._pkg.has(rels[rid]):
                    found.add(rels[rid])
        return sorted(found)

    @staticmethod
    def _part_label(part: str) -> str:
        if part == "word/document.xml":
            return "document"
        return posixpath.splitext(posixpath.basename(part))[0]

    def _walk_part(self, root: ET.Element, part: str) -> None:
        for para in self._iter_accepted(root, w("p")):
            self._process_paragraph(para, part)

    def _iter_accepted(self, root: ET.Element, tag: str) -> Iterable[ET.Element]:
        """深度优先遍历，跳过 del/moveFrom 子树，产出匹配标签的元素。"""
        stack = [root]
        while stack:
            elem = stack.pop()
            if elem.tag in _EXCLUDED_CONTAINERS:
                continue
            if elem.tag == tag:
                yield elem
            stack.extend(reversed(list(elem)))

    def _process_paragraph(self, para: ET.Element, part: str) -> None:
        ppr = para.find(w("pPr"))
        para_style = None
        if ppr is not None:
            pstyle = ppr.find(w("pStyle"))
            if pstyle is not None:
                para_style = pstyle.get(w("val"))
        for run in self._iter_accepted(para, w("r")):
            self._process_run(run, para_style, part)

    def _process_run(self, run: ET.Element, para_style: Optional[str], part: str) -> None:
        rpr = run.find(w("rPr"))
        char_style = None
        if rpr is not None:
            rstyle = rpr.find(w("rStyle"))
            if rstyle is not None:
                char_style = rstyle.get(w("val"))
        layers = self.styles.layers(rpr, char_style, para_style)
        if _first(layers, "vanish") is True:
            return
        lang = _first(layers, "lang_east_asia")
        text = "".join(t.text or "" for t in run.iter(w("t")))
        if not text:
            return
        for slot, chunk in self._split_slots(text):
            self._emit(part, chunk, slot, layers, lang)

    @staticmethod
    def _split_slots(text: str) -> Iterable[tuple[str, str]]:
        slot = _slot_of(text[0])
        start = 0
        for i in range(1, len(text)):
            current = _slot_of(text[i])
            if current != slot:
                yield slot, text[start:i]
                slot, start = current, i
        yield slot, text[start:]

    def _emit(
        self,
        part: str,
        text: str,
        slot: str,
        layers: list[RunProps],
        lang: Optional[str],
    ) -> None:
        ref = _first(layers, slot)
        if ref is None:
            self.result.errors.append(UnresolvedError(part, text, slot, "missing-font"))
            return
        if ref.literal is not None:
            self.result.segments.append(FontSegment(part, text, slot, ref.literal))
            return
        font, reason = self.theme.resolve(ref.theme, slot, lang)
        if font is None:
            self.result.errors.append(
                UnresolvedError(part, text, slot, reason or "missing-font"))
        else:
            self.result.segments.append(FontSegment(part, text, slot, font))


def inspect(path: str) -> InspectResult:
    """检查 DOCX，返回全部有效字体片段与未解析错误。"""
    return _Checker(path).run()


def validate(path: str, allowed_fonts) -> ValidateResult:
    """按字体白名单（名称精确匹配）校验，返回全部违规与未解析错误。"""
    allowed = set(allowed_fonts)
    result = inspect(path)
    violations = [
        Violation(seg.part, seg.text, seg.slot, seg.font)
        for seg in result.segments
        if seg.font not in allowed
    ]
    return ValidateResult(violations=violations, errors=result.errors)
