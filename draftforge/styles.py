"""样式层解析：docDefaults、段落样式、字符样式及 basedOn 链。"""
from __future__ import annotations

from xml.etree.ElementTree import Element

from .model import RunProperties
from .package import W_NS, qn


def _w(tag: str) -> str:
    return qn(W_NS, tag)


def parse_rpr(rpr: Element | None) -> RunProperties:
    """把一个 w:rPr 元素解析为 RunProperties 层；缺失属性保持 None。"""
    props = RunProperties()
    if rpr is None:
        return props
    rfonts = rpr.find(_w("rFonts"))
    if rfonts is not None:
        props.ascii_font = rfonts.get(_w("ascii"))
        props.ascii_theme = rfonts.get(_w("asciiTheme"))
        props.hansi_font = rfonts.get(_w("hAnsi"))
        props.hansi_theme = rfonts.get(_w("hAnsiTheme"))
        props.eastasia_font = rfonts.get(_w("eastAsia"))
        props.eastasia_theme = rfonts.get(_w("eastAsiaTheme"))
    lang = rpr.find(_w("lang"))
    if lang is not None:
        props.lang_eastasia = lang.get(_w("eastAsia"))
    vanish = rpr.find(_w("vanish"))
    if vanish is not None:
        val = vanish.get(_w("val"))
        props.vanish = val not in ("false", "0", "off")
    return props


class _Style:
    def __init__(self, element: Element) -> None:
        self.style_id = element.get(_w("styleId"))
        self.type = element.get(_w("type"))
        self.is_default = element.get(_w("default")) in ("1", "true")
        based_on = element.find(_w("basedOn"))
        self.based_on = based_on.get(_w("val")) if based_on is not None else None
        self.rpr = parse_rpr(element.find(_w("rPr")))


class StyleSheet:
    """按优先级提供 run 属性层（高到低）。"""

    def __init__(self, styles_root: Element) -> None:
        self._styles: dict = {}
        self._default_paragraph_id: str | None = None
        for element in styles_root.findall(_w("style")):
            style = _Style(element)
            self._styles[style.style_id] = style
            if style.type == "paragraph" and style.is_default:
                self._default_paragraph_id = style.style_id
        defaults = styles_root.find(_w("docDefaults"))
        rpr_default = defaults.find(_w("rPrDefault")) if defaults is not None else None
        rpr = rpr_default.find(_w("rPr")) if rpr_default is not None else None
        self._doc_defaults = parse_rpr(rpr)

    def doc_defaults(self) -> RunProperties:
        return self._doc_defaults

    def _chain(self, style_id: str | None) -> list:
        layers = []
        current = self._styles.get(style_id) if style_id else None
        while current is not None:
            layers.append(current.rpr)
            current = self._styles.get(current.based_on) if current.based_on else None
        return layers

    def paragraph_layers(self, style_id: str | None) -> list:
        """段落样式及其 basedOn 链，离使用点最近者优先。"""
        if style_id is None:
            style_id = self._default_paragraph_id
        return self._chain(style_id)

    def character_layers(self, style_id: str | None) -> list:
        """字符样式及其 basedOn 链；未指定字符样式时为空。"""
        if style_id is None:
            return []
        return self._chain(style_id)
