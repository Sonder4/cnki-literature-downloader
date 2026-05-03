# CNKI 文献下载与综述技能

这是一个面向中文学术写作场景的开源技能与脚本集合，用于把 CNKI 上的文献检索、下载、筛选、全文分析、文献综述生成和参考文献格式化串成一条可复用工作流。

它的定位不是“绕过平台限制的抓取器”，而是“在用户已经合法登录并可访问 CNKI 的前提下，帮助用户更稳定地完成文献整理”。

浏览器自动化能力已经封装在 `scripts/cnki_browser_session.py` 中。实际使用时，通常只需要调用本仓库提供的 Python 脚本，不需要手写 `browser-harness` 命令串。

## 功能概览

- 基于已登录 Chrome 会话检索 CNKI
- 从结果页提取候选元数据
- 进入详情页执行 `PDF下载`，优先 PDF，CAJ 仅归档
- 对下载结果做落盘验证与失败重试
- 结合全文 Markdown 做二次筛选
- 生成评分表、筛选报告、文献综述草稿
- 生成可直接复用的参考文献格式
- 输出 `\bibitem{}` 片段，便于接入本地 LaTeX 流程

## 目录结构

```text
.
├── SKILL.md
├── README.md
├── LICENSE
├── .gitignore
├── agents/
│   └── openai.yaml
├── references/
│   ├── browser-automation-contract.md
│   ├── reference-format-profiles.md
│   └── scoring-rules.md
├── scripts/
│   ├── cnki_browser_session.py
│   ├── cnki_extract_candidates.py
│   ├── cnki_download_batch.py
│   ├── cnki_archive_caj.py
│   ├── score_cnki_candidates.py
│   ├── format_cnki_references.py
│   ├── build_literature_review.py
│   └── cnki_profiles.py
└── docs/
    └── 内容审查报告.md
```

## 依赖

### 必需

- Python 3.10+
- 一个已经登录 CNKI 的 Chrome 会话
- [`browser-harness`](https://github.com/browser-use/browser-harness) 运行时，用作底层浏览器控制层

### 可选

- MinerU 或其他 PDF 转 Markdown 工具
- 本地 LaTeX 环境，用于消费 `bibliography_ready_*.tex`

## 使用流程

### 1. 准备浏览器会话

```bash
python scripts/cnki_browser_session.py prepare-session
```

如果这里失败，先检查：

- Chrome 是否已启动
- 是否已登录 CNKI
- `browser-harness` 是否可用

### 2. 提取候选文献

```bash
python scripts/cnki_extract_candidates.py \
  --query "三维激光雷达 移动机器人 定位" \
  --query "点云 SLAM 重定位" \
  --output-root output/CNKI_20260503
```

### 3. 候选评分

```bash
python scripts/score_cnki_candidates.py \
  output/CNKI_20260503/cnki_candidates_20260503.json \
  --profile gbt7714-thesis-numeric \
  --topic "移动机器人定位导航" \
  --output output/CNKI_20260503/评分表_20260503.csv
```

### 4. 批量下载

```bash
python scripts/cnki_download_batch.py \
  output/CNKI_20260503/cnki_candidates_20260503.json \
  --journal-dir output/CNKI_20260503/期刊 \
  --degree-dir output/CNKI_20260503/学位论文 \
  --output-log output/CNKI_20260503/cnki_download_log_20260503.json
```

### 5. 全文提取与综述输出

先用你自己的 PDF 提取链生成 Markdown，再执行：

```bash
python scripts/build_literature_review.py \
  output/CNKI_20260503/评分表_20260503.csv \
  --topic "移动机器人定位导航" \
  --content-root output/CNKI_20260503 \
  --output output/CNKI_20260503/文献综述草稿_20260503.md
```

### 6. 参考文献格式化

```bash
python scripts/format_cnki_references.py \
  output/CNKI_20260503/评分表_20260503.csv \
  --profile gbt7714-thesis-numeric \
  --content-root output/CNKI_20260503 \
  --output-dir output/CNKI_20260503/引用输出
```

输出包括：

- `参考文献格式清单_<date>.md`
- `citation_candidates_<date>.csv`
- `bibliography_ready_<date>.tex`

## 参考文献格式

当前内置两个 profile：

- `gbt7714-thesis-numeric`
- `generic-cn-academic`

其中：

- `gbt7714-thesis-numeric` 更适合中文论文、毕业设计、技术报告
- `generic-cn-academic` 更适合一般性的文献整理与导出

具体规则见 [references/reference-format-profiles.md](references/reference-format-profiles.md)。

## 合规边界

本仓库默认遵守以下边界：

- 不导出或复制浏览器 cookie
- 不包含任何账号密码处理逻辑
- 不实现绕过权限验证的下载方式
- 不鼓励超速批量抓取
- 默认通过详情页可见的 `PDF下载` 按钮进行交互

这套工具应只用于你自己合法可访问的文献资源。

## 隐私与安全

发布前已做过一轮内容审查，重点移除了：

- 本地绝对路径
- 特定学校论文模板引用
- 当前私有项目目录结构
- 仅适用于某一篇论文的内部链接

审查说明见 [docs/内容审查报告.md](docs/内容审查报告.md)。

## 已知限制

- 依赖 CNKI 页面结构，若站点改版需要更新脚本
- 依赖用户本地 Chrome 已登录状态
- 目前没有内置 PDF 转 Markdown 引擎
- 引用格式是“可直接复用的初稿”，正式入稿前仍建议人工复核

## 许可

本项目采用 [MIT License](LICENSE)。
