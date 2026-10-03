"""用标准库 zipfile 生成真实 DOCX 压缩包的测试辅助。"""

from __future__ import annotations

import zipfile

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PR = "http://schemas.openxmlformats.org/package/2006/relationships"

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>
"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{pr}">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
""".format(pr=PR)


def document_rels(extra: list[tuple[str, str, str]] = ()) -> str:
    """extra: (rId, type, target) 列表。"""
    items = [
        '<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    ]
    for rid, rtype, target in extra:
        items.append(
            '<Relationship Id="{rid}" Type="{rtype}" Target="{target}"/>'.format(
                rid=rid, rtype=rtype, target=target))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="{pr}">{items}</Relationships>'
    ).format(pr=PR, items="".join(items))


def make_docx(path: str, parts: dict[str, str]) -> None:
    """parts: 部件名 -> XML 文本。自动补齐 [Content_Types].xml 与根关系。"""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("_rels/.rels", ROOT_RELS)
        for name, content in parts.items():
            zf.writestr(name, content)
