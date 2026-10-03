"""DOCX 压缩包读取与 XML 解析辅助。"""

from __future__ import annotations

import posixpath
import xml.etree.ElementTree as ET
import zipfile

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PR_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def qn(ns: str, tag: str) -> str:
    return "{%s}%s" % (ns, tag)


def w(tag: str) -> str:
    return qn(W_NS, tag)


class DocxPackage:
    """按需读取 DOCX 压缩包内的 XML 部件。"""

    def __init__(self, path: str):
        self._zip = zipfile.ZipFile(path)

    def close(self) -> None:
        self._zip.close()

    def __enter__(self) -> "DocxPackage":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def read_xml(self, name: str) -> ET.Element:
        with self._zip.open(name) as fh:
            return ET.parse(fh).getroot()

    def has(self, name: str) -> bool:
        return name in self._zip.namelist()

    def rels_name(self, part_name: str) -> str:
        base = posixpath.basename(part_name)
        return posixpath.join(posixpath.dirname(part_name), "_rels", base + ".rels")

    def read_rels(self, part_name: str) -> dict[str, str]:
        """返回 {rId: 解析后的目标部件名}。仅处理内部目标。"""
        rels_name = self.rels_name(part_name)
        result: dict[str, str] = {}
        if not self.has(rels_name):
            return result
        root = self.read_xml(rels_name)
        base_dir = posixpath.dirname(part_name)
        for rel in root.iter(qn(PR_NS, "Relationship")):
            rid = rel.get("Id")
            target = rel.get("Target")
            mode = rel.get("TargetMode", "Internal")
            if not rid or not target or mode == "External":
                continue
            result[rid] = posixpath.normpath(posixpath.join(base_dir, target))
        return result
