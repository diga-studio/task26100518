"""样式层级解析：docDefaults、段落样式、字符样式及 basedOn 链。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import xml.etree.ElementTree as ET

from .docx import w


@dataclass(frozen=True)
class FontRef:
    """一个槽位上的字体引用：字面字体或主题引用。"""

    literal: Optional[str] = None
    theme: Optional[str] = None  # "major" 或 "minor"


@dataclass
class RunProps:
    """单层 run 属性。None 表示该层未指定，继续向低优先级查找。"""

    ascii: Optional[FontRef] = None
    eastAsia: Optional[FontRef] = None
    hAnsi: Optional[FontRef] = None
    lang_east_asia: Optional[str] = None
    vanish: Optional[bool] = None


_THEME_ATTRS = {
    "ascii": "asciiTheme",
    "eastAsia": "eastAsiaTheme",
    "hAnsi": "hAnsiTheme",
}

_THEME_VALUES = {
    "majorAscii": "major",
    "majorEastAsia": "major",
    "majorHAnsi": "major",
    "minorAscii": "minor",
    "minorEastAsia": "minor",
    "minorHAnsi": "minor",
}


def _parse_bool(elem: ET.Element) -> bool:
    """on/off 类型：无 val 为 true，显式 false/0 为 false。"""
    val = elem.get(w("val"))
    if val is None:
        return True
    return val not in ("false", "0", "off")


def parse_rpr(rpr: Optional[ET.Element]) -> RunProps:
    """把 w:rPr 元素解析为单层 RunProps。

    同一槽位同层同时存在字面字体与 Theme 属性时，主题引用优先。
    """
    props = RunProps()
    if rpr is None:
        return props
    rfonts = rpr.find(w("rFonts"))
    if rfonts is not None:
        for slot in ("ascii", "eastAsia", "hAnsi"):
            literal = rfonts.get(w(slot))
            theme_attr = rfonts.get(w(_THEME_ATTRS[slot]))
            theme = _THEME_VALUES.get(theme_attr) if theme_attr else None
            if theme is not None:
                setattr(props, slot, FontRef(theme=theme))
            elif literal is not None:
                setattr(props, slot, FontRef(literal=literal))
    lang = rpr.find(w("lang"))
    if lang is not None:
        ea = lang.get(w("eastAsia"))
        if ea is not None:
            props.lang_east_asia = ea
    vanish = rpr.find(w("vanish"))
    if vanish is not None:
        props.vanish = _parse_bool(vanish)
    return props


@dataclass
class _Style:
    style_id: str
    type: str
    based_on: Optional[str]
    props: RunProps


class StyleSheet:
    """styles.xml 的解析结果，提供按优先级排序的 RunProps 层。"""

    def __init__(self, root: ET.Element):
        self._styles: dict[str, _Style] = {}
        self.default_paragraph_style: Optional[str] = None
        self.doc_defaults = RunProps()
        defaults = root.find(w("docDefaults"))
        if defaults is not None:
            rpr_default = defaults.find(w("rPrDefault"))
            if rpr_default is not None:
                self.doc_defaults = parse_rpr(rpr_default.find(w("rPr")))
        for style in root.findall(w("style")):
            style_id = style.get(w("styleId"))
            if not style_id:
                continue
            stype = style.get(w("type"), "paragraph")
            based_on_el = style.find(w("basedOn"))
            based_on = based_on_el.get(w("val")) if based_on_el is not None else None
            self._styles[style_id] = _Style(
                style_id=style_id,
                type=stype,
                based_on=based_on,
                props=parse_rpr(style.find(w("rPr"))),
            )
            if stype == "paragraph" and style.get(w("default")) in ("1", "true"):
                self.default_paragraph_style = style_id

    def _chain(self, style_id: Optional[str]) -> list[RunProps]:
        """样式及其 basedOn 链，离使用点最近者优先。basedOn 保证无环。"""
        layers: list[RunProps] = []
        current = style_id
        while current is not None and current in self._styles:
            style = self._styles[current]
            layers.append(style.props)
            current = style.based_on
        return layers

    def layers(
        self,
        run_rpr: Optional[ET.Element],
        char_style_id: Optional[str],
        para_style_id: Optional[str],
    ) -> list[RunProps]:
        """返回从高到低优先级的 RunProps 层。

        顺序：run 直接属性、字符样式链、段落样式链、docDefaults。
        未指定段落样式时使用默认段落样式；未指定字符样式时跳过该层。
        """
        result = [parse_rpr(run_rpr)]
        if char_style_id is not None:
            result.extend(self._chain(char_style_id))
        if para_style_id is None:
            para_style_id = self.default_paragraph_style
        result.extend(self._chain(para_style_id))
        result.append(self.doc_defaults)
        return result
