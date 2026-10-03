"""DraftForge 公开操作测试（真实 DOCX 压缩包）。"""
import os
import tempfile
import unittest

import draftforge
from tests.docx_factory import (
    document_xml, header_rel, header_xml, script_font, styles_xml,
    theme_xml, write_docx,
)


class DocxTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = os.path.join(self._tmp.name, "sample.docx")


class MixedRunSlotsTest(DocxTestCase):
    """一个 run 混合 ASCII/中文/扩展拉丁，三个槽分别来自不同层。"""

    def setUp(self):
        super().setUp()
        styles = styles_xml(
            doc_defaults_rpr='<w:rFonts w:ascii="DefA" w:hAnsi="DefH" w:eastAsia="DefE"/>',
            styles=(
                '<w:style w:type="paragraph" w:styleId="P1">'
                '<w:rPr><w:rFonts w:hAnsi="ParaHAnsi"/></w:rPr></w:style>'
                '<w:style w:type="character" w:styleId="C1">'
                '<w:rPr><w:rFonts w:eastAsia="CharEA"/></w:rPr></w:style>'
            ),
        )
        document = document_xml(
            '<w:p><w:pPr><w:pStyle w:val="P1"/></w:pPr>'
            '<w:r><w:rPr><w:rStyle w:val="C1"/>'
            '<w:rFonts w:ascii="RunAscii"/></w:rPr>'
            '<w:t>A中é</w:t></w:r></w:p>'
        )
        write_docx(self.path, document, styles, theme_xml())

    def test_segments(self):
        segments = draftforge.inspect(self.path)
        self.assertEqual(
            [(s.text, s.font, s.error) for s in segments],
            [("A", "RunAscii", None), ("中", "CharEA", None), ("é", "ParaHAnsi", None)],
        )

    def test_validate(self):
        violations = draftforge.validate(self.path, {"RunAscii", "CharEA"})
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].text, "é")
        self.assertEqual(violations[0].font, "ParaHAnsi")
        self.assertEqual(violations[0].reason, "font_not_allowed")


class ThemeEaFallbackAndVanishTest(DocxTestCase):
    """默认段落样式提供语言；主题 ea 为空走脚本项；高层显式取消 vanish。"""

    def setUp(self):
        super().setUp()
        styles = styles_xml(
            doc_defaults_rpr=(
                '<w:rFonts w:asciiTheme="minorAscii" w:hAnsiTheme="minorAscii" '
                'w:eastAsiaTheme="minorEastAsia"/><w:vanish/>'
            ),
            styles=(
                '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
                '<w:rPr><w:vanish w:val="0"/><w:lang w:eastAsia="zh-CN"/></w:rPr>'
                '</w:style>'
            ),
        )
        theme = theme_xml(minor_ea="", minor_scripts=script_font("Hans", "HansFont"))
        document = document_xml(
            '<w:p><w:r><w:t>中A</w:t></w:r>'
            '<w:r><w:rPr><w:vanish/></w:rPr><w:t>XYZ</w:t></w:r></w:p>'
        )
        write_docx(self.path, document, styles, theme)

    def test_segments(self):
        segments = draftforge.inspect(self.path)
        self.assertEqual(
            [(s.text, s.font, s.error) for s in segments],
            [("中", "HansFont", None), ("A", "MinorLatin", None)],
        )

    def test_validate(self):
        violations = draftforge.validate(self.path, {"MinorLatin"})
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].text, "中")
        self.assertEqual(violations[0].font, "HansFont")


class StructureTraversalTest(DocxTestCase):
    """页眉引用、表格、超链接、ins/moveTo 计入，del/moveFrom 排除。"""

    def setUp(self):
        super().setUp()
        styles = styles_xml(
            doc_defaults_rpr='<w:rFonts w:ascii="Body" w:hAnsi="Body" w:eastAsia="Body"/>',
            styles="",
        )
        document = document_xml(
            '<w:p><w:ins><w:r><w:t>I1</w:t></w:r></w:ins>'
            '<w:del><w:r><w:t>D1</w:t></w:r></w:del>'
            '<w:moveFrom><w:r><w:t>M1</w:t></w:r></w:moveFrom>'
            '<w:moveTo><w:r><w:t>M2</w:t></w:r></w:moveTo>'
            '<w:hyperlink><w:r><w:t>L1</w:t></w:r></w:hyperlink></w:p>'
            '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>T1</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
            '<w:p><w:pPr><w:sectPr>'
            '<w:headerReference w:type="default" r:id="rHdr1"/>'
            '</w:sectPr></w:pPr></w:p>'
        )
        header = header_xml(
            '<w:p><w:r><w:rPr><w:rFonts w:ascii="HdrFont"/></w:rPr>'
            '<w:t>H1</w:t></w:r></w:p>'
        )
        write_docx(
            self.path, document, styles, theme_xml(),
            extra_parts={"word/header1.xml": header},
            extra_rels=header_rel("rHdr1", "header1.xml"),
        )

    def test_segments(self):
        segments = draftforge.inspect(self.path)
        got = [(s.text, s.font, s.part) for s in segments]
        self.assertIn(("I1M2L1T1", "Body", "document"), got)
        self.assertIn(("H1", "HdrFont", "word/header1.xml"), got)
        texts = "".join(s.text for s in segments)
        self.assertNotIn("D1", texts)
        self.assertNotIn("M1", texts)


class UnresolvedFontTest(DocxTestCase):
    """所有层都未指定字体时报告未解析错误。"""

    def setUp(self):
        super().setUp()
        write_docx(
            self.path,
            document_xml('<w:p><w:r><w:t>中</w:t></w:r></w:p>'),
            styles_xml(doc_defaults_rpr="", styles=""),
            theme_xml(),
        )

    def test_inspect_error(self):
        segments = draftforge.inspect(self.path)
        self.assertEqual(len(segments), 1)
        self.assertIsNone(segments[0].font)
        self.assertIn("eastAsia", segments[0].error)

    def test_validate_unresolved(self):
        violations = draftforge.validate(self.path, {"Body"})
        self.assertEqual(len(violations), 1)
        self.assertTrue(violations[0].reason.startswith("unresolved:"))


if __name__ == "__main__":
    unittest.main()
