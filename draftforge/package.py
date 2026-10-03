"""DOCX 压缩包读取：解析主文档、样式、主题及页眉页脚部件。"""
from __future__ import annotations

import posixpath
import zipfile
from xml.etree.ElementTree import Element, fromstring

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

_HEADER_FOOTER_TYPES = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/header",
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer",
)


def qn(ns: str, tag: str) -> str:
    return "{%s}%s" % (ns, tag)


class DocxPackage:
    """已打开的 DOCX 包，按需解析各 XML 部件。"""

    def __init__(self, path: str) -> None:
        self._zip = zipfile.ZipFile(path)
        self._cache: dict = {}

    def _part(self, name: str) -> Element:
        if name not in self._cache:
            self._cache[name] = fromstring(self._zip.read(name))
        return self._cache[name]

    def document(self) -> Element:
        return self._part("word/document.xml")

    def styles(self) -> Element:
        return self._part("word/styles.xml")

    def theme(self) -> Element:
        rels = self._rels("word/_rels/document.xml.rels")
        for rel in rels:
            if rel.get("Type", "").endswith("/theme"):
                return self._part(posixpath.join("word", rel.get("Target")))
        raise KeyError("theme part not found")

    def _rels(self, name: str) -> list:
        try:
            root = self._part(name)
        except KeyError:
            return []
        return list(root)

    def header_footer_parts(self) -> list:
        """返回被任一 sectPr 通过关系引用的页眉/页脚 (part_name, root) 列表。"""
        rels = {
            rel.get("Id"): rel
            for rel in self._rels("word/_rels/document.xml.rels")
            if rel.get("Type") in _HEADER_FOOTER_TYPES
        }
        seen = []
        r_id_attr = qn(R_NS, "id")
        for sect_pr in self.document().iter(qn(W_NS, "sectPr")):
            for ref in sect_pr:
                if ref.tag in (qn(W_NS, "headerReference"), qn(W_NS, "footerReference")):
                    rel = rels.get(ref.get(r_id_attr))
                    if rel is None:
                        continue
                    part_name = posixpath.normpath(posixpath.join("word", rel.get("Target")))
                    if part_name not in [name for name, _ in seen]:
                        seen.append((part_name, self._part(part_name)))
        return seen
