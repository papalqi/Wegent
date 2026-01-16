# Wegent

> 🚀 一个开源的 AI 原生操作系统，用于定义、组织和运行智能体团队

[English](README.md) | 简体中文

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.68+-green.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15+-black.svg)](https://nextjs.org)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://docker.com)
[![Claude](https://img.shields.io/badge/Claude-Code-orange.svg)](https://claude.ai)
[![Gemini](https://img.shields.io/badge/Gemini-支持-4285F4.svg)](https://ai.google.dev)
[![Version](https://img.shields.io/badge/版本-1.35.2-brightgreen.svg)](https://github.com/wecode-ai/wegent/releases)

<div align="center">

<img src="https://github.com/user-attachments/assets/677abce3-bd3f-4064-bdab-e247b142c22f" width="100%" alt="Chat Mode Demo"/>

<img src="https://github.com/user-attachments/assets/85e08e2f-5f52-4275-b349-0b5703664c2c" width="100%" alt="Knowledge Demo"/>

<img src="https://github.com/user-attachments/assets/cc25c415-d3f1-4e9f-a64c-1d2614d69c7d" width="100%" alt="Code Mode Demo"/>

[快速开始](#-快速开始) · [文档](docs/README.md) · [开发指南](docs/guides/developer/setup.md)

</div>

---

## ✨ 核心模式

| 💬 对话模式 | 💻 编码模式 | 📚 知识模式 |
|:------------|:------------|:-----------------------|
| **LLM**: 支持Claude / OpenAI / Gemini 等主流模型<br>**多模态**: 支持图片 / PPT / Word / PDF / Excel 文件自动解析<br>**联网搜索**: 支持对接各类搜索引擎<br>**深度调研**: 支持深度调研模式，可自动搜索、整理、生成调研报告<br>**纠错模式**: 由多个AI自动检测并修正回答中的错误<br>**追问模式**: AI 主动追问澄清需求，确保理解准确<br>**扩展能力**: 支持 Skill 技能包 / MCP 工具 / 自定义工具 | **多平台集成**: 支持GitHub / GitLab / Gitea / Gitee / Gerrit平台<br>**自动化AI工作流**: 分支 → 编码 → 提交 → PR 流程自动化<br>**需求澄清**: AI 主动追问，确保理解准确<br>**Wiki 生成**: 自动生成代码库文档 | **RAG 检索**: 向量 / 关键词 / 混合检索<br>**存储后端**: Elasticsearch / Qdrant<br>**文档解析**: PDF / Markdown / DOCX / 代码文件<br>**Wiki**: 代码库文档自动生成 |

---

## 🔧 扩展能力

- **智能体生成向导**: 4 步创建: 描述需求 → AI 追问 → 实时微调 → 一键创建
- **协作模式**: 支持开箱即用的 4 种多Agent协作模式（顺序/并行/路由/循环），灵活组合多个 Bot
- **支持Skill**: 动态加载技能包，提升 Token 效率
- **MCP 工具**: Model Context Protocol，调用外部工具和服务
- **执行引擎**: 支持ClaudeCode / Agno 沙箱隔离执行，Dify API 代理，Chat 直连模式4个执行引擎
- **YAML 配置**: Kubernetes 风格 CRD，定义 Ghost / Bot / Team / Skill
- **API**: 对外提供 OpenAI 兼容接口，方便与其他系统集成

---

## 🚀 快速开始

```bash
git clone https://github.com/wecode-ai/wegent.git && cd wegent
cp .env.example .env
# 修改 .env 中的 REDIS_PASSWORD（docker-compose 默认启用 Redis AUTH）
docker-compose up -d
# 访问 http://localhost:3000
```

然后在浏览器中访问 http://localhost:3000

> 可选：启用 RAG 功能 `docker compose --profile rag up -d`

### 🌐 公网 / 局域网访问（start.sh）

`start.sh` 会在本机启动前后端（Docker 启动 MySQL/Redis/Executor Manager）。如果需要让其他机器访问，请用 `WEGENT_PUBLIC_HOST` 指定对外可访问的地址：

```bash
# 自动探测本机非回环 IPv4（推荐）
WEGENT_PUBLIC_HOST=auto ./start.sh

# 或显式指定公网 IP/域名
WEGENT_PUBLIC_HOST=your-public-ip-or-domain ./start.sh
```

可选：`WEGENT_PUBLIC_SCHEME=https`（配合反向代理/HTTPS）、`WEGENT_FRONTEND_HOST=127.0.0.1`（限制前端仅本机访问）。

### 💾 持久化代码目录（/wegent_repos）

`start.sh` 会把宿主机上的持久化目录挂载进执行器容器的 `/wegent_repos`，用于 UI「目录」模式的代码工作区（不会自动 clone/sync，也不会被任务删除）。

默认路径是仓库同级的 `../wegent_repos`。如果系统盘容量不够，建议把它放到更大的磁盘/分区：

```bash
WEGENT_PERSIST_REPO_ROOT=/data/wegent_repos ./start.sh
```

也可以把 `WEGENT_PERSIST_REPO_ROOT=/data/wegent_repos` 写进仓库根目录的 `.env.local`（`start.sh` 会自动读取）。该目录必须在 Wegent 仓库外部。

---

## 📦 预置智能体

| 团队 | 用途 |
|------|------|
| chat-team | 通用 AI 助手 + Mermaid 图表 |
| translator | 多语言翻译 |
| dev-team | Git 工作流：分支 → 编码 → 提交 → PR |
| wiki-team | 代码库 Wiki 文档生成 |

---

## 🏗️ 架构

```
Frontend (Next.js) → Backend (FastAPI) → Executor Manager → Executors (ClaudeCode/Agno)
```

**核心概念：**
- **Ghost** (提示词) + **Shell** (执行环境) + **Model** = **Bot**
- 多个 **Bot** + **协作模式** = **Team**

> 详见 [核心概念](docs/concepts/core-concepts.md) | [YAML 规范](docs/reference/yaml-specification.md)

---

## 🤝 贡献

我们欢迎贡献！详情请参阅 [贡献指南 (CONTRIBUTING.md)](CONTRIBUTING.md) 和 [中文速查指南 (AGENTS.md)](AGENTS.md)。

### Git 分支策略

**⚠️ 重要分支保护规则：**

- **main 分支**：仅限生产就绪代码。**禁止直接提交**。只接受来自 `develop` 分支的 Pull Request。
- **develop 分支**：开发集成分支。接受来自 `feature/*`、`fix/*`、`hotfix/*` 分支的 PR。
- **功能分支**：从 `develop` 创建，PR 回 `develop`。

**工作流程：**
```bash
git checkout develop && git pull origin develop
git checkout -b feature/your-feature develop
# ... 开发 ...
git push origin feature/your-feature
# 创建 PR: feature/your-feature → develop
```

### CI / 镜像发布

- **Publish Image 工作流**（`.github/workflows/publish-image.yml`）触发条件：
  - 合并到 `main` 的 PR，且 **标题包含** `Changeset version bump`
  - 推送标签 `v*.*.*`（如 `v1.35.2`）
  - 手动 `workflow_dispatch`
- 若 PR 合并但标题不含 `Changeset version bump`，Actions 里可能会显示为 **Skipped**（job 被 `if:` 条件跳过）。
- **Tests 工作流**（`.github/workflows/test.yml`）在所有推送到 `main`/`develop` 和所有 PR 时运行。

### 🧪 Chrome DevTools MCP（可选：交互式回归 / 调试）

适用场景：需要用 MCP 客户端驱动真实 Chrome（查看 Console / Network / DOM 等），用于补充 Playwright 自动化回归或排查 flaky。

**依赖：**
- 已安装 Google Chrome
- Node.js `>= 20.19.0`（`chrome-devtools-mcp` 要求；低版本会直接报错）
- （可选）Codex CLI（本仓库的 Codex 技能会用到）

**配置（Codex CLI）：**
```bash
# 添加 MCP server（全局）
codex mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest

# 查看已配置的 MCP servers
codex mcp list
```

常见问题：如果提示 `chrome-devtools-mcp does not support Node ...`，请升级 Node 到 `>= 20.19.0`（或在 Codex 配置中指定更新的 Node/`npx`）。

> Wegent 内部的 MCP（Chat Shell）开关与服务列表请参考：`docs/guides/developer/config-web-search-and-mcp.md`。

## 📞 支持

- 🐛 问题反馈：[GitHub Issues](https://github.com/wecode-ai/wegent/issues)
- 💬 Discord：[加入社区](https://discord.gg/MVzJzyqEUp)

## 👥 贡献者

感谢以下开发者的贡献，让这个项目变得更好 💪

<!-- readme: contributors -start -->
<table>
<tr>
    <td align="center">
        <a href="https://github.com/qdaxb">
            <img src="https://avatars.githubusercontent.com/u/4157870?v=4" width="80;" alt="qdaxb"/>
            <br />
            <sub><b>Axb</b></sub>
        </a>
    </td>
    <td align="center">
        <a href="https://github.com/feifei325">
            <img src="https://avatars.githubusercontent.com/u/46489071?v=4" width="80;" alt="feifei325"/>
            <br />
            <sub><b>Feifei</b></sub>
        </a>
    </td>
    <td align="center">
        <a href="https://github.com/Micro66">
            <img src="https://avatars.githubusercontent.com/u/27556103?v=4" width="80;" alt="Micro66"/>
            <br />
            <sub><b>MicroLee</b></sub>
        </a>
    </td>
    <td align="center">
        <a href="https://github.com/cc-yafei">
            <img src="https://avatars.githubusercontent.com/u/78540184?v=4" width="80;" alt="cc-yafei"/>
            <br />
            <sub><b>YaFei Liu</b></sub>
        </a>
    </td>
    <td align="center">
        <a href="https://github.com/johnny0120">
            <img src="https://avatars.githubusercontent.com/u/15564476?v=4" width="80;" alt="johnny0120"/>
            <br />
            <sub><b>Johnny0120</b></sub>
        </a>
    </td>
    <td align="center">
        <a href="https://github.com/kissghosts">
            <img src="https://avatars.githubusercontent.com/u/3409715?v=4" width="80;" alt="kissghosts"/>
            <br />
            <sub><b>Yanhe</b></sub>
        </a>
    </td>
    <td align="center">
        <a href="https://github.com/moqimoqidea">
            <img src="https://avatars.githubusercontent.com/u/39821951?v=4" width="80;" alt="moqimoqidea"/>
            <br />
            <sub><b>Moqimoqidea</b></sub>
        </a>
    </td>
    <td align="center">
        <a href="https://github.com/2561056571">
            <img src="https://avatars.githubusercontent.com/u/112464849?v=4" width="80;" alt="2561056571"/>
            <br />
            <sub><b>Xuemin</b></sub>
        </a>
    </td></tr>
<tr>
    <td align="center">
        <a href="https://github.com/joyway1978">
            <img src="https://avatars.githubusercontent.com/u/184585080?v=4" width="80;" alt="joyway1978"/>
            <br />
            <sub><b>Joyway78</b></sub>
        </a>
    </td>
    <td align="center">
        <a href="https://github.com/FicoHu">
            <img src="https://avatars.githubusercontent.com/u/19767574?v=4" width="80;" alt="FicoHu"/>
            <br />
            <sub><b>FicoHu</b></sub>
        </a>
    </td>
    <td align="center">
        <a href="https://github.com/junbaor">
            <img src="https://avatars.githubusercontent.com/u/10198622?v=4" width="80;" alt="junbaor"/>
            <br />
            <sub><b>Junbaor</b></sub>
        </a>
    </td>
    <td align="center">
        <a href="https://github.com/icycrystal4">
            <img src="https://avatars.githubusercontent.com/u/946207?v=4" width="80;" alt="icycrystal4"/>
            <br />
            <sub><b>icycrystal4</b></sub>
        </a>
    </td>
    <td align="center">
        <a href="https://github.com/maquan0927">
            <img src="https://avatars.githubusercontent.com/u/40860588?v=4" width="80;" alt="maquan0927"/>
            <br />
            <sub><b>Just Quan</b></sub>
        </a>
    </td>
    <td align="center">
        <a href="https://github.com/fengkuizhi">
            <img src="https://avatars.githubusercontent.com/u/3616484?v=4" width="80;" alt="fengkuizhi"/>
            <br />
            <sub><b>Fengkuizhi</b></sub>
        </a>
    </td>
    <td align="center">
        <a href="https://github.com/jolestar">
            <img src="https://avatars.githubusercontent.com/u/77268?v=4" width="80;" alt="jolestar"/>
            <br />
            <sub><b>Jolestar</b></sub>
        </a>
    </td>
    <td align="center">
        <a href="https://github.com/andrewzq777">
            <img src="https://avatars.githubusercontent.com/u/223815624?v=4" width="80;" alt="andrewzq777"/>
            <br />
            <sub><b>Andrewzq777</b></sub>
        </a>
    </td></tr>
<tr>
    <td align="center">
        <a href="https://github.com/graindt">
            <img src="https://avatars.githubusercontent.com/u/3962041?v=4" width="80;" alt="graindt"/>
            <br />
            <sub><b>Graindt</b></sub>
        </a>
    </td>
    <td align="center">
        <a href="https://github.com/parabala">
            <img src="https://avatars.githubusercontent.com/u/115564000?v=4" width="80;" alt="parabala"/>
            <br />
            <sub><b>parabala</b></sub>
        </a>
    </td></tr>
</table>
<!-- readme: contributors -end -->

---

<p align="center">由 WeCode-AI 团队用 ❤️ 制作</p>
