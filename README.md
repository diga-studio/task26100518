# task26100518

## DraftForge：DOCX 字体合规检查库

纯 Python 标准库实现，供文档保存时同步调用，无任何第三方依赖。

### 使用

```python
import draftforge

# 输出全部有效字体片段与未解析错误
result = draftforge.inspect("report.docx")
for seg in result.segments:
    print(seg.part, seg.text, seg.slot, seg.font)
for err in result.errors:
    print("未解析:", err.part, err.text, err.slot, err.reason)

# 按字体白名单（名称精确匹配）输出全部违规
check = draftforge.validate("report.docx", allowed_fonts={"宋体", "Times New Roman"})
for v in check.violations:
    print("违规:", v.part, v.text, v.slot, v.font)
```

### 行为要点

- 检查正文及任一 `sectPr` 引用的页眉页脚；遍历表格与超链接内文字。
- 接受修订视图：`ins`/`moveTo` 计入，`del`/`moveFrom` 排除；只处理 `w:t`。
- 属性优先级：run 直接属性 > 字符样式链 > 段落样式链 > docDefaults，
  `rFonts` 三槽、`lang.eastAsia`、`vanish` 各自独立继承。
- 字符分派：ASCII → `ascii`，U+4E00–U+9FFF → `eastAsia`，其余 → `hAnsi`。
- 主题引用按 major/minor 取主题字体组；`ea` 为空时按 `lang.eastAsia`
  选择脚本项（`zh-CN`→`Hans`，`zh-TW`→`Hant`），失败报告未解析。
- 白名单校验只针对可见字符的有效字体；未使用样式中的字体不产生违规。

### 测试

```bash
python3 -m unittest discover -s tests -t . -v
```
