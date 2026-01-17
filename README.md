# Wegent

> 🚀 An open-source AI-native operating system to define, organize, and run intelligent agent teams

English | [简体中文](README_zh.md)

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.68+-green.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15+-black.svg)](https://nextjs.org)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://docker.com)
[![Claude](https://img.shields.io/badge/Claude-Code-orange.svg)](https://claude.ai)
[![Gemini](https://img.shields.io/badge/Gemini-supported-4285F4.svg)](https://ai.google.dev)
[![Version](https://img.shields.io/badge/version-1.35.2-brightgreen.svg)](https://github.com/wecode-ai/wegent/releases)

<div align="center">

<img src="https://github.com/user-attachments/assets/677abce3-bd3f-4064-bdab-e247b142c22f" width="100%" alt="Chat Mode Demo"/>

<img src="https://github.com/user-attachments/assets/85e08e2f-5f52-4275-b349-0b5703664c2c" width="100%" alt="Knowledge Demo"/>

<img src="https://github.com/user-attachments/assets/cc25c415-d3f1-4e9f-a64c-1d2614d69c7d" width="100%" alt="Code Mode Demo"/>

[Quick Start](#-quick-start) · [Documentation](docs/README.md) · [Development Guide](docs/guides/developer/setup.md)

</div>

---

## ✨ Core Modes

| 💬 Chat Mode | 💻 Code Mode | 📚 Knowledge Mode |
|:-------------|:-------------|:-----------------------------------|
| **LLM**: Supports Claude / OpenAI / Gemini and other mainstream models<br>**Multimodal**: Supports automatic parsing of images / PPT / Word / PDF / Excel files<br>**Web Search**: Supports integration with various search engines<br>**Deep Research**: Supports deep research mode with automatic search, organization, and report generation<br>**Error Correction**: Multiple AIs automatically detect and correct errors in responses<br>**Follow-up Mode**: AI proactively asks clarifying questions to ensure accurate understanding<br>**Extensions**: Supports Skill packages / MCP tools / Custom tools | **Multi-platform Integration**: Supports GitHub / GitLab / Gitea / Gitee / Gerrit platforms<br>**Automated AI Workflow**: Branch → Code → Commit → PR automation<br>**Requirement Clarification**: AI proactively asks questions to ensure accurate understanding<br>**Wiki Generation**: Automatic codebase documentation generation | **RAG Retrieval**: Vector / Keyword / Hybrid retrieval<br>**Storage Backends**: Elasticsearch / Qdrant<br>**Document Parsing**: PDF / Markdown / DOCX / Code files<br>**Wiki**: Automatic codebase documentation generation |

---

## 🔧 Extensibility

- **Agent Creation Wizard**: 4-step creation: Describe requirements → AI asks questions → Real-time fine-tuning → One-click create
- **Collaboration Modes**: 4 out-of-the-box multi-Agent collaboration modes (Sequential/Parallel/Router/Loop), flexible combination of multiple Bots
- **Skill Support**: Dynamically load skill packages to improve Token efficiency
- **MCP Tools**: Model Context Protocol for calling external tools and services
- **Execution Engines**: Supports ClaudeCode / Agno sandboxed isolation, Dify API proxy, Chat direct mode - 4 execution engines
- **YAML Config**: Kubernetes-style CRD for defining Ghost / Bot / Team / Skill
- **API**: Provides OpenAI-compatible interface for easy integration with other systems

---

## 🚀 Quick Start

```bash
git clone https://github.com/wecode-ai/wegent.git && cd wegent
cp .env.example .env
# Update REDIS_PASSWORD in .env (docker-compose enables Redis AUTH by default)
docker-compose up -d
# Open http://localhost:3000
```

Then open http://localhost:3000 in your browser.

> Optional: Enable RAG features with `docker compose --profile rag up -d`

### 🌐 Public / LAN Access (start.sh)

`start.sh` runs backend + frontend on host (and starts MySQL/Redis/Executor Manager via Docker). To make it accessible from other machines, set `WEGENT_PUBLIC_HOST` to a reachable address:

```bash
# Auto-detect a non-loopback IPv4 (recommended)
WEGENT_PUBLIC_HOST=auto ./start.sh

# Or specify your public IP / domain
WEGENT_PUBLIC_HOST=your-public-ip-or-domain ./start.sh
```

Optional: `WEGENT_PUBLIC_SCHEME=https` (behind reverse proxy/HTTPS), `WEGENT_FRONTEND_HOST=127.0.0.1` (restrict frontend to local only).

### 💾 Persistent Code Workspace (/wegent_repos)

`start.sh` mounts a host directory into executor containers at `/wegent_repos` for the UI “Directory” mode (Wegent won’t auto clone/sync, and tasks won’t delete it).

By default it uses `../wegent_repos` (sibling of the Wegent repo). If your system disk is too small, point it to a larger disk/partition:

```bash
WEGENT_PERSIST_REPO_ROOT=/data/wegent_repos ./start.sh
```

You can also put `WEGENT_PERSIST_REPO_ROOT=/data/wegent_repos` into the repo root `.env.local` (auto-loaded by `start.sh`).
The path must be outside the Wegent repo root.

---

## 📦 Built-in Agents

| Team | Purpose |
|------|---------|
| chat-team | General AI assistant + Mermaid diagrams |
| translator | Multi-language translation |
| dev-team | Git workflow: branch → code → commit → PR |
| wiki-team | Codebase Wiki documentation generation |

---

## 🏗️ Architecture

```
Frontend (Next.js) → Backend (FastAPI) → Executor Manager → Executors (ClaudeCode/Agno/Dify/Chat)
```

**Core Concepts:**
- **Ghost** (prompt) + **Shell** (environment) + **Model** = **Bot**
- Multiple **Bots** + **Collaboration Mode** = **Team**

> See [Core Concepts](docs/concepts/core-concepts.md) | [YAML Spec](docs/reference/yaml-specification.md)

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) and [中文贡献指南 (AGENTS.md)](AGENTS.md) for details.

### Git Branch Strategy

**⚠️ Important Branch Protection Rules:**

- **main branch**: Production-ready code only. **NO direct commits allowed**. Only accepts Pull Requests from `develop` branch.
- **develop branch**: Development integration branch. Accepts PRs from `feature/*`, `fix/*`, `hotfix/*` branches.
- **Feature branches**: Create from `develop`, PR back to `develop`.

**Workflow:**
```bash
git checkout develop && git pull origin develop
git checkout -b feature/your-feature develop
# ... do your work ...
git push origin feature/your-feature
# Create PR: feature/your-feature → develop
```

### CI / Image Publishing

- **Publish Image workflow** (`.github/workflows/publish-image.yml`) triggers on:
  - PR merged into `main` **with title containing** `Changeset version bump`
  - tag push `v*.*.*` (e.g., `v1.35.2`)
  - manual `workflow_dispatch`
- If a PR is merged without `Changeset version bump` in the title, the workflow may show as **Skipped** (jobs gated by `if:` conditions).
- **Tests workflow** (`.github/workflows/test.yml`) runs on all pushes to `main`/`develop` and all PRs.

### 🧪 Chrome DevTools MCP (Optional: Interactive Regression / Debugging)

Use case: drive a real Chrome instance via an MCP client (inspect Console / Network / DOM) to complement Playwright E2E or debug flaky UI tests.

**Dependencies:**
- Google Chrome installed
- Node.js `>= 20.19.0` (required by `chrome-devtools-mcp`; older versions will fail)
- (Optional) Codex CLI

**Setup (Codex CLI):**
```bash
# Add an MCP server (global)
codex mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest

# List configured MCP servers
codex mcp list
```

Troubleshooting: if you see `chrome-devtools-mcp does not support Node ...`, upgrade Node to `>= 20.19.0` (or configure Codex to use a newer Node/`npx`).

> For Wegent's built-in MCP (Chat Shell) configuration, see `docs/guides/developer/config-web-search-and-mcp.md`.

## 📞 Support

- 🐛 Issues: [GitHub Issues](https://github.com/wecode-ai/wegent/issues)
- 💬 Discord: [Join our community](https://discord.gg/MVzJzyqEUp)

## 👥 Contributors

Thanks to the following developers for their contributions and efforts to make this project better. 💪

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

<p align="center">Made with ❤️ by WeCode-AI Team</p>
