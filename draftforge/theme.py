"""主题字体解析与主题引用求值。"""
from __future__ import annotations

from xml.etree.ElementTree import Element

from .model import ThemeFonts
from .package import A_NS, qn

_LANG_TO_SCRIPT = {
    "zh-CN": "Hans",
    "zh-TW": "Hant",
}


def _a(tag: str) -> str:
    return qn(A_NS, tag)


def _parse_font_group(group: Element) -> tuple:
    latin = group.find(_a("latin"))
    ea = group.find(_a("ea"))
    scripts = {}
    for font in group.findall(_a("font")):
        scripts[font.get("script")] = font.get("typeface", "")
    return (
        latin.get("typeface", "") if latin is not None else "",
        ea.get("typeface", "") if ea is not None else "",
        scripts,
    )


def parse_theme(theme_root: Element) -> ThemeFonts:
    scheme = theme_root.find(".//" + _a("fontScheme"))
    fonts = ThemeFonts()
    if scheme is None:
        return fonts
    major = scheme.find(_a("majorFont"))
    if major is not None:
        fonts.major_latin, fonts.major_ea, fonts.major_scripts = _parse_font_group(major)
    minor = scheme.find(_a("minorFont"))
    if minor is not None:
        fonts.minor_latin, fonts.minor_ea, fonts.minor_scripts = _parse_font_group(minor)
    return fonts


def resolve_theme_slot(theme: ThemeFonts, slot: str, theme_ref: str,
                       lang_eastasia: str | None) -> tuple:
    """把 asciiTheme/hAnsiTheme/eastAsiaTheme 引用求值为具体字体名。

    返回 (font_name, error)；无法解析时 font_name 为 None。
    """
    if theme_ref.startswith("major"):
        latin, ea, scripts = theme.major_latin, theme.major_ea, theme.major_scripts
    elif theme_ref.startswith("minor"):
        latin, ea, scripts = theme.minor_latin, theme.minor_ea, theme.minor_scripts
    else:
        return None, "未知主题引用 %r" % theme_ref

    if slot in ("ascii", "hAnsi"):
        if latin:
            return latin, None
        return None, "主题 %s latin 字体为空" % theme_ref

    # eastAsia 槽
    if ea:
        return ea, None
    script = _LANG_TO_SCRIPT.get(lang_eastasia)
    if script is None:
        return None, "主题 ea 为空且语言 %r 不受支持" % lang_eastasia
    font = scripts.get(script)
    if font:
        return font, None
    return None, "主题 %s 缺少脚本项 %r" % (theme_ref, script)
