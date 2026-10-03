# DraftForge DOCX 字体合规检查库

纯 Python 标准库实现，供文档保存时同步调用，检查 DOCX 中每个可见字符的有效字体是否符合白名单。

## 使用

```python
import draftforge

# 有效字体片段：每个可见字符唯一归属一个有效字体或未解析错误
segments = draftforge.inspect("doc.docx")
for seg in segments:
    print(seg.text, seg.font, seg.error, seg.part)

# 白名单校验（按名称精确匹配），输出全部违规
violations = draftforge.validate("doc.docx", allowed_fonts={"Arial", "宋体"})
for v in violations:
    print(v.text, v.font, v.reason, v.part)
```

- `inspect(path) -> list[FontSegment]`：`FontSegment(text, font, error, part)`；
  `font` 为 `None` 时 `error` 给出未解析原因。`part` 标识来源部件
  （`document` 或 `word/header1.xml` 等）。
- `validate(path, allowed_fonts) -> list[Violation]`：`Violation(text, font, reason, part)`；
  `reason` 为 `font_not_allowed` 或 `unresolved: <原因>`。

## 规则概要

- 范围：正文 + 任一 sectPr 通过关系引用的页眉/页脚；遍历表格与超链接；
  计入 `ins`/`moveTo`，排除 `del`/`moveFrom`；只处理 `w:t`；有效 vanish 为 true 的 run 不可见。
- 属性优先级（高到低）：run 直接属性 → 字符样式及 basedOn 链 → 段落样式及 basedOn 链
  → docDefaults；`rFonts` 各槽、`lang.eastAsia`、`vanish` 分别继承。
- 字符分派：ASCII → `ascii`，U+4E00–U+9FFF → `eastAsia`，其余 → `hAnsi`。
- 主题引用：`ascii`/`hAnsi` 取主题 latin，`eastAsia` 取 ea；ea 为空时按
  `lang.eastAsia` 选脚本项（`zh-CN`→Hans，`zh-TW`→Hant），否则报告未解析。

## 测试

```bash
python3 -m unittest discover -s tests -v
```

测试会动态生成真实的 DOCX 压缩包并直接调用公开操作。
