"""生成真实 DOCX 压缩包的测试辅助。"""
from __future__ import annotations

import zipfile

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/word/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
</Types>
"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rTheme" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>
  {extra}
</Relationships>
"""

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def document_xml(body_inner: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="%s" xmlns:r="%s"><w:body>%s</w:body></w:document>'
        % (W, R, body_inner)
    )


def styles_xml(doc_defaults_rpr: str, styles: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:styles xmlns:w="%s">'
        '<w:docDefaults><w:rPrDefault><w:rPr>%s</w:rPr></w:rPrDefault></w:docDefaults>'
        '%s</w:styles>' % (W, doc_defaults_rpr, styles)
    )


def theme_xml(major_latin="MajorLatin", major_ea="MajorEA",
              minor_latin="MinorLatin", minor_ea="MinorEA",
              major_scripts="", minor_scripts="") -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<a:theme xmlns:a="%s" name="Test"><a:themeElements>'
        '<a:clrScheme name="T"><a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>'
        '<a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>'
        '<a:dk2><a:srgbClr val="1F497D"/></a:dk2><a:lt2><a:srgbClr val="EEECE1"/></a:lt2>'
        '<a:accent1><a:srgbClr val="4F81BD"/></a:accent1><a:accent2><a:srgbClr val="C0504D"/></a:accent2>'
        '<a:accent3><a:srgbClr val="9BBB59"/></a:accent3><a:accent4><a:srgbClr val="8064A2"/></a:accent4>'
        '<a:accent5><a:srgbClr val="4BACC6"/></a:accent5><a:accent6><a:srgbClr val="F79646"/></a:accent6>'
        '<a:hlink><a:srgbClr val="0000FF"/></a:hlink><a:folHlink><a:srgbClr val="800080"/></a:folHlink>'
        '</a:clrScheme>'
        '<a:fontScheme name="Test">'
        '<a:majorFont><a:latin typeface="%s"/><a:ea typeface="%s"/>%s</a:majorFont>'
        '<a:minorFont><a:latin typeface="%s"/><a:ea typeface="%s"/>%s</a:minorFont>'
        '</a:fontScheme>'
        '<a:fmtScheme name="Test"><a:fillStyleLst/><a:lnStyleLst/><a:effectStyleLst/>'
        '<a:bgFillStyleLst/></a:fmtScheme>'
        '</a:themeElements></a:theme>'
        % (A, major_latin, major_ea, major_scripts,
           minor_latin, minor_ea, minor_scripts)
    )


def script_font(script: str, typeface: str) -> str:
    return '<a:font script="%s" typeface="%s"/>' % (script, typeface)


def header_xml(inner: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:hdr xmlns:w="%s" xmlns:r="%s">%s</w:hdr>' % (W, R, inner)
    )


def write_docx(path, document: str, styles: str, theme: str,
               extra_parts: dict | None = None, extra_rels: str = "") -> None:
    """写出最小但真实的 DOCX 压缩包。"""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("word/document.xml", document)
        zf.writestr("word/styles.xml", styles)
        zf.writestr("word/theme/theme1.xml", theme)
        zf.writestr("word/_rels/document.xml.rels", _RELS.format(extra=extra_rels))
        for name, content in (extra_parts or {}).items():
            zf.writestr(name, content)


def header_rel(rel_id: str, target: str) -> str:
    return (
        '<Relationship Id="%s" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" '
        'Target="%s"/>' % (rel_id, target)
    )
