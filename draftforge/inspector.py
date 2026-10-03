"""核心检查逻辑：遍历可见文字并计算每个字符的有效字体。"""
from __future__ import annotations

from xml.etree.ElementTree import Element

from .model import FontSegment, Violation
from .package import W_NS, DocxPackage, qn
from .styles import StyleSheet, parse_rpr
from .theme import parse_theme, resolve_theme_slot

_SKIP_SUBTREE = frozenset({
    qn(W_NS, "del"),
    qn(W_NS, "moveFrom"),
    qn(W_NS, "txbxContent"),
})

_FLOW_CONTAINERS = frozenset({
    qn(W_NS, "document"),
    qn(W_NS, "body"),
    qn(W_NS, "hdr"),
    qn(W_NS, "ftr"),
    qn(W_NS, "tbl"),
    qn(W_NS, "tr"),
    qn(W_NS, "tc"),
    qn(W_NS, "p"),
    qn(W_NS, "hyperlink"),
    qn(W_NS, "ins"),
    qn(W_NS, "moveTo"),
    qn(W_NS, "sdt"),
    qn(W_NS, "sdtContent"),
    qn(W_NS, "smartTag"),
})


def _slot_for(char: str) -> str:
    code = ord(char)
    if code < 128:
        return "ascii"
    if 0x4E00 <= code <= 0x9FFF:
        return "eastAsia"
    return "hAnsi"


def _resolve_vanish(layers: list) -> bool:
    for layer in layers:
        if layer.vanish is not None:
            return layer.vanish
    return False


def _resolve_lang(layers: list) -> str | None:
    for layer in layers:
        if layer.lang_eastasia is not None:
            return layer.lang_eastasia
    return None


def _resolve_slot(layers: list, slot: str, theme, lang_eastasia: str | None) -> tuple:
    """按层高到低解析一个字体槽，返回 (font_name, error)。"""
    font_attr = {"ascii": "ascii_font", "hAnsi": "hansi_font",
                 "eastAsia": "eastasia_font"}[slot]
    theme_attr = {"ascii": "ascii_theme", "hAnsi": "hansi_theme",
                  "eastAsia": "eastasia_theme"}[slot]
    for layer in layers:
        theme_ref = getattr(layer, theme_attr)
        if theme_ref:
            return resolve_theme_slot(theme, slot, theme_ref, lang_eastasia)
        literal = getattr(layer, font_attr)
        if literal:
            return literal, None
    return None, "槽 %s 未指定字体" % slot


def _iter_paragraphs(element: Element):
    """按文档顺序产出可见区域内的 w:p（跳过 del/moveFrom/文本框）。"""
    if element.tag in _SKIP_SUBTREE:
        return
    if element.tag == qn(W_NS, "p"):
        yield element
        return
    if element.tag not in _FLOW_CONTAINERS:
        return
    for child in element:
        yield from _iter_paragraphs(child)


def _iter_runs(paragraph: Element):
    """产出段落内可见的 w:r（进入超链接与 ins/moveTo，跳过删除内容）。"""
    for child in paragraph:
        if child.tag in _SKIP_SUBTREE:
            continue
        if child.tag == qn(W_NS, "r"):
            yield child
        elif child.tag in _FLOW_CONTAINERS:
            yield from _iter_runs(child)


def _paragraph_style_id(paragraph: Element) -> str | None:
    ppr = paragraph.find(qn(W_NS, "pPr"))
    if ppr is None:
        return None
    pstyle = ppr.find(qn(W_NS, "pStyle"))
    return pstyle.get(qn(W_NS, "val")) if pstyle is not None else None


def _run_style_id(rpr: Element | None) -> str | None:
    if rpr is None:
        return None
    rstyle = rpr.find(qn(W_NS, "rStyle"))
    return rstyle.get(qn(W_NS, "val")) if rstyle is not None else None


def _run_segments(run: Element, paragraph_style_id: str | None,
                  stylesheet: StyleSheet, theme, part: str) -> list:
    rpr = run.find(qn(W_NS, "rPr"))
    run_layer = parse_rpr(rpr)
    layers = (
        [run_layer]
        + stylesheet.character_layers(_run_style_id(rpr))
        + stylesheet.paragraph_layers(paragraph_style_id)
        + [stylesheet.doc_defaults()]
    )
    if _resolve_vanish(layers):
        return []
    lang_eastasia = _resolve_lang(layers)
    segments = []
    for node in run:
        if node.tag != qn(W_NS, "t"):
            continue
        for char in node.text or "":
            slot = _slot_for(char)
            font, error = _resolve_slot(layers, slot, theme, lang_eastasia)
            if segments and segments[-1].font == font and segments[-1].error == error:
                segments[-1].text += char
            else:
                segments.append(FontSegment(text=char, font=font, error=error, part=part))
    return segments


def _merge_adjacent(segments: list) -> list:
    merged = []
    for seg in segments:
        if merged and merged[-1].font == seg.font and merged[-1].error == seg.error \
                and merged[-1].part == seg.part:
            merged[-1].text += seg.text
        else:
            merged.append(seg)
    return merged


def inspect(path: str) -> list:
    """返回文档中全部可见文字的有效字体片段（FontSegment 列表）。"""
    package = DocxPackage(path)
    stylesheet = StyleSheet(package.styles())
    theme = parse_theme(package.theme())
    parts = [("document", package.document())]
    parts.extend(package.header_footer_parts())

    segments = []
    for part_name, root in parts:
        for paragraph in _iter_paragraphs(root):
            style_id = _paragraph_style_id(paragraph)
            for run in _iter_runs(paragraph):
                segments.extend(_run_segments(run, style_id, stylesheet, theme, part_name))
    return _merge_adjacent(segments)


def validate(path: str, allowed_fonts) -> list:
    """返回全部违规：字体不在白名单，或字体无法解析。"""
    allowed = set(allowed_fonts)
    violations = []
    for segment in inspect(path):
        if segment.error is not None:
            violations.append(Violation(
                text=segment.text, font=None,
                reason="unresolved: " + segment.error, part=segment.part))
        elif segment.font not in allowed:
            violations.append(Violation(
                text=segment.text, font=segment.font,
                reason="font_not_allowed", part=segment.part))
    return violations
