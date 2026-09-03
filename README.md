# RAG Document Finder

一个用于发现和验证多模态 RAG 测试文档的 Codex Skill。

它不只根据标题搜索 PDF，还会在获得下载文件后分析真实版式：页数、图片
覆盖率、稀疏文本视觉页、操作步骤、图注以及可检测的表格，从而筛选更适合
图文检索、表格检索和操作流程问答的测试集。

## 适用场景

- 寻找企业软件操作手册、工业设备安装手册和 SOP
- 寻找有截图、图示、参数表、接线表或连续步骤的公开 PDF
- 为多模态 RAG 验证图片提取、表格解析、图文关联和检索召回
- 筛选纯图片、图文混合、表格嵌图等不同版式的基准文档

## 安装

将仓库克隆到 Codex 的用户 Skill 目录：

```powershell
git clone https://github.com/1m55555555/rag-document-finder.git `
  $env:USERPROFILE\.codex\skills\rag-document-finder
```

重新打开 Codex 会话后，可用 `$rag-document-finder` 显式调用；默认也允许按
任务自动匹配。

## 使用示例

```text
使用 $rag-document-finder 帮我寻找 3 份适合多模态 RAG 测试的公开 PDF。

要求：
1. 中文或中英混合的企业软件操作手册、工业安装手册或 SOP；
2. 页数在 15 到 60 页；
3. 有连续操作步骤、界面截图或安装示意图；
4. 至少包含表格、参数表或接线表中的一种；
5. 仅接受厂商官网、政府、高校或标准组织来源的直接 PDF 链接；
6. 排除营销画册、产品目录和没有实际步骤的介绍材料；
7. 下载后检查图片页、步骤页、图注页和表格页；
8. 按匹配度评分，并说明每份文档适合验证的 RAG 环节。
```

## 验证逻辑

Skill 先将自然语言需求转换为文档约束，再用多组关键词搜索可信来源。对每个
候选 PDF，`scripts/inspect_pdf.py` 会输出页面级报告：

- `page_count`：总页数
- `image_pages`：视觉内容覆盖面积较高的页面
- `sparse_text_visual_pages`：文字很少但视觉内容明显的页面
- `procedure_pages`：含编号步骤线索的页面
- `caption_pages`：含图号或表号线索的页面
- `detected_table_pages`：由 PyMuPDF 表格检测器识别到的页面
- `probable_table_pages`：表格检测或文本线索推断出的页面

示例命令：

```powershell
python scripts/inspect_pdf.py .\candidate.pdf --output .\candidate-report.json
```

脚本采用页面 bbox 覆盖面积计算图片比例，避免 PDF 中多个重叠图片层被简单
累加后误判为“整页图片”。表格检测是候选证据，不应替代对最终渲染页面的人工
确认。

## 评分

候选文档按以下维度评分：

| 维度 | 权重 |
| --- | ---: |
| 来源可信度 | 25% |
| 版式与目标匹配度 | 25% |
| 图片、图示与表格价值 | 20% |
| 步骤连续性 | 15% |
| 页数符合度 | 10% |
| 下载与解析质量 | 5% |

详细规则见 [references/scoring-rubric.md](references/scoring-rubric.md)。

## 目录结构

```text
rag-document-finder/
├─ SKILL.md                     # Codex 调用规则和边界
├─ agents/openai.yaml           # UI 元数据和自动调用策略
├─ references/scoring-rubric.md # 候选评分规则
└─ scripts/inspect_pdf.py       # PDF 页级版式分析脚本
```

## 边界

- 不绕过登录、付费墙、robots 限制或访问控制。
- 不自动把候选文档上传、入库或删除；这些是独立操作。
- 搜索结果页不是版式证据，只有下载后的实际 PDF 分析才可作为确认依据。
- 一般输出 3 到 5 份已验证候选；没有完全符合的文档时，明确说明差距。

## 依赖

```text
Python 3.10+
PyMuPDF
```

安装 PyMuPDF：

```powershell
pip install pymupdf
```
