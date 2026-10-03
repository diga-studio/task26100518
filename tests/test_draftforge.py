"""DraftForge 公开操作的端到端测试：生成真实 DOCX 压缩包后直接调用。"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import draftforge
from tests.docx_factory import A, R, W, document_rels, make_docx

W_DECL = 'xmlns:w="%s"' % W
R_DECL = 'xmlns:r="%s"' % R


def _document(body: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document %s %s><w:body>%s</w:body></w:document>'
    ) % (W_DECL, R_DECL, body)


def _styles(inner: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:styles %s>%s</w:styles>'
    ) % (W_DECL, inner)


class DraftForgeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmp.name, "sample.docx")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_mixed_run_slot_resolution(self) -> None:
        """一个 run 混合 ASCII/中文/扩展拉丁，三个槽分别来自直接格式、
        字符样式、段落样式。"""
        styles = _styles(
            '<w:docDefaults><w:rPrDefault><w:rPr>'
            '<w:rFonts w:ascii="DefaultAscii" w:hAnsi="DefaultHansi" w:eastAsia="DefaultEA"/>'
            '</w:rPr></w:rPrDefault></w:docDefaults>'
            '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
            '<w:rPr><w:rFonts w:ascii="ParaAscii"/></w:rPr></w:style>'
            '<w:style w:type="character" w:styleId="MyChar">'
            '<w:rPr><w:rFonts w:eastAsia="CharEA"/></w:rPr></w:style>'
            '<w:style w:type="character" w:styleId="Unused">'
            '<w:rPr><w:rFonts w:ascii="UnusedFont"/></w:rPr></w:style>'
        )
        document = _document(
            '<w:p><w:pPr><w:pStyle w:val="Normal"/></w:pPr>'
            '<w:r><w:rPr><w:rStyle w:val="MyChar"/>'
            '<w:rFonts w:hAnsi="DirectHansi"/></w:rPr>'
            '<w:t>ab中文é</w:t></w:r></w:p>'
        )
        make_docx(self.path, {
            "word/document.xml": document,
            "word/styles.xml": styles,
            "word/_rels/document.xml.rels": document_rels(),
        })

        result = draftforge.inspect(self.path)
        self.assertEqual(result.errors, [])
        self.assertEqual(
            [(s.part, s.text, s.slot, s.font) for s in result.segments],
            [
                ("document", "ab", "ascii", "ParaAscii"),
                ("document", "中文", "eastAsia", "CharEA"),
                ("document", "é", "hAnsi", "DirectHansi"),
            ],
        )

        check = draftforge.validate(
            self.path, {"ParaAscii", "CharEA", "DefaultAscii", "DefaultHansi"})
        self.assertEqual(check.errors, [])
        self.assertEqual(
            [(v.text, v.slot, v.font) for v in check.violations],
            [("é", "hAnsi", "DirectHansi")],
        )
        # 未使用样式中的字体不得产生违规。
        self.assertNotIn("UnusedFont", {s.font for s in result.segments})

    def test_theme_script_fallback_and_vanish_override(self) -> None:
        """默认段落样式提供语言，主题 ea 为空时按脚本项解析；
        高层显式取消 vanish 后原本隐藏的文字必须被检查。"""
        theme = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<a:theme xmlns:a="%s"><a:themeElements><a:fontScheme name="x">'
            '<a:majorFont><a:latin typeface="MajorLatin"/><a:ea typeface=""/></a:majorFont>'
            '<a:minorFont><a:latin typeface="MinorLatin"/><a:ea typeface=""/>'
            '<a:font script="Hans" typeface="ThemeHans"/>'
            '<a:font script="Hant" typeface="ThemeHant"/>'
            '</a:minorFont></a:fontScheme></a:themeElements></a:theme>'
        ) % A
        styles = _styles(
            '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
            '<w:rPr><w:rFonts w:eastAsiaTheme="minorEastAsia"/>'
            '<w:lang w:eastAsia="zh-CN"/><w:vanish/></w:rPr></w:style>'
        )
        document = _document(
            '<w:p><w:r><w:rPr><w:vanish w:val="0"/></w:rPr>'
            '<w:t>隐藏字</w:t></w:r>'
            '<w:r><w:t>真隐藏</w:t></w:r></w:p>'
        )
        make_docx(self.path, {
            "word/document.xml": document,
            "word/styles.xml": styles,
            "word/theme/theme1.xml": theme,
            "word/_rels/document.xml.rels": document_rels([
                ("rIdTheme",
                 "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme",
                 "theme/theme1.xml"),
            ]),
        })

        result = draftforge.inspect(self.path)
        self.assertEqual(result.errors, [])
        self.assertEqual(
            [(s.text, s.slot, s.font) for s in result.segments],
            [("隐藏字", "eastAsia", "ThemeHans")],
        )

        check = draftforge.validate(self.path, {"OtherFont"})
        self.assertEqual(
            [(v.text, v.font) for v in check.violations],
            [("隐藏字", "ThemeHans")],
        )

    def test_headers_revisions_and_unresolved(self) -> None:
        """sectPr 引用的页眉被检查；ins/moveTo 计入、del/moveFrom 排除；
        所有来源都缺字体时报告未解析错误。"""
        styles = _styles(
            '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
            '<w:rPr><w:rFonts w:ascii="BodyAscii" w:hAnsi="BodyHansi" '
            'w:eastAsia="BodyEA"/></w:rPr></w:style>'
            '<w:style w:type="paragraph" w:styleId="Bare"/>'
        )
        document = _document(
            '<w:p>'
            '<w:r><w:t>正文</w:t></w:r>'
            '<w:ins><w:r><w:t>插入</w:t></w:r></w:ins>'
            '<w:del><w:r><w:t>删除</w:t></w:r></w:del>'
            '<w:moveFrom><w:r><w:t>移出</w:t></w:r></w:moveFrom>'
            '<w:moveTo><w:r><w:t>移入</w:t></w:r></w:moveTo>'
            '</w:p>'
            '<w:p><w:pPr><w:pStyle w:val="Bare"/></w:pPr>'
            '<w:r><w:t>XY</w:t></w:r></w:p>'
            '<w:sectPr><w:headerReference w:type="default" r:id="rIdHdr"/></w:sectPr>'
        )
        header = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:hdr %s><w:p><w:r><w:t>页眉</w:t></w:r></w:p></w:hdr>'
        ) % W_DECL
        make_docx(self.path, {
            "word/document.xml": document,
            "word/styles.xml": styles,
            "word/header1.xml": header,
            "word/_rels/document.xml.rels": document_rels([
                ("rIdHdr",
                 "http://schemas.openxmlformats.org/officeDocument/2006/relationships/header",
                 "header1.xml"),
            ]),
        })

        result = draftforge.inspect(self.path)
        self.assertEqual(
            [(s.part, s.text, s.font) for s in result.segments],
            [
                ("document", "正文", "BodyEA"),
                ("document", "插入", "BodyEA"),
                ("document", "移入", "BodyEA"),
                ("header1", "页眉", "BodyEA"),
            ],
        )
        self.assertEqual(
            [(e.part, e.text, e.slot, e.reason) for e in result.errors],
            [("document", "XY", "ascii", "missing-font")],
        )

        check = draftforge.validate(self.path, {"BodyEA"})
        self.assertEqual(check.violations, [])
        self.assertEqual(len(check.errors), 1)


if __name__ == "__main__":
    unittest.main()
