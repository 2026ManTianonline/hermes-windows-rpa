# Hermes Windows RPA

> 基于 Hermes Agent 的 Windows 桌面 UI 自动化方案  
> 截图 → 视觉识别 → MCP 执行 → 循环验证 的完整 RPA 闭环
可实现微信群聊，QQ群聊等一系列社交平台互动功能，但要自己写提示词教有视觉模型的AI如GPT5.4等来进行你想实现的效果
---

## 项目简介

本项目实现了一套运行在 **WSL (Ubuntu) + Hermes Agent** 环境下的 Windows 桌面 RPA 方案。通过截图+视觉模型理解 UI 界面，再通过 MCP 服务器操控鼠标键盘，实现类似 Claude Computer Use / OpenAI CUA 的桌面自动化能力。

### 架构概览

```
┌─────────────────────────────────────────────────────┐
│  Hermes Agent (WSL)                                  │
│                                                       │
│  ┌──────────────────────────────────────────────────┐│
│  │  Native MCP Client                                ││
│  │  └─ mcp_desktop_screenshot()                      ││
│  │  └─ mcp_desktop_click(x, y)                       ││
│  │  └─ mcp_desktop_type_text(text)                   ││
│  │  └─ mcp_desktop_get_screen_size()                 ││
│  └──────────┬───────────────────────────────────────┘│
│             │ stdio                                   │
└─────────────┼─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────┐
│  vadgr-computer-use MCP Server  v0.3.0               │
│  21 tools (screenshot, click, type, scroll, etc.)     │
│  └─ TCP localhost:19542                               │
└─────────────┬─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────┐
│  Windows 桥接守护进程 (daemon.py)                      │
│  运行在 Windows 端, 监听 :19542                        │
│  └─ mss 原生截图 (2560×1600, 毫秒级)                   │
│  └─ Win32 SendInput 鼠标键盘操控                       │
└─────────────────────────────────────────────────────┘
```

### 技术栈

| 组件 | 技术 |
|------|------|
| AI Agent | [Hermes Agent](https://hermes-agent.nousresearch.com) |
| MCP 服务器 | [vadgr-computer-use](https://github.com/MONTBRAIN/vadgr-computer-use) v0.3.0 |
| 截图引擎 | mss (Windows Desktop Duplication API) |
| 鼠标键盘 | Win32 SendInput |
| 视觉模型 | GPT-4o / Qwen2.5-VL / Kimi-K2.6 (任选) |
| 运行环境 | Windows 11 + WSL2 (Ubuntu) |

---

## 快速开始

### 前置条件

- Windows 11 24H2+ / Windows 10 22H2+
- WSL2 已启用 (Ubuntu 22.04/24.04)
- Hermes Agent 已安装

### 1. 安装 MCP 服务器

```bash
# 创建虚拟环境
python3 -m venv ~/.hermes/venvs/rpa

# 安装 vadgr-computer-use
~/.hermes/venvs/rpa/bin/pip install vadgr-computer-use

# 验证
~/.hermes/venvs/rpa/bin/vadgr-cua doctor
```

### 2. 配置 Hermes MCP

```bash
# 添加 MCP 服务器
hermes mcp add desktop \
  --command ~/.hermes/venvs/rpa/bin/vadgr-cua \
  --args '["--transport","stdio"]'

# 验证连接
hermes mcp test desktop
```

> ⚠️ 如果 `hermes mcp add` 生成的 args 格式不对，手动编辑 `~/.hermes/config.yaml`：
> ```yaml
> mcp_servers:
>   desktop:
>     command: /home/h/.hermes/venvs/rpa/bin/vadgr-cua
>     args:
>       - --transport
>       - stdio
>     enabled: true
> ```

### 3. 启动 Windows 桥接守护进程

```bash
# 自动部署 (如果 Windows Python 在标准路径)
~/.hermes/venvs/rpa/bin/vadgr-cua install-daemon

# 或手动启动
cmd.exe /c "start /B python C:\Users\<用户名>\vadgr\daemon.py --port 19542"
```

### 4. 验证

```bash
# 检查 daemon
~/.hermes/venvs/rpa/bin/vadgr-cua doctor

# 检查 MCP 连接
hermes mcp test desktop

# 在 Hermes 会话中测试
mcp_desktop_get_screen_size()   # → 1366x853
mcp_desktop_screenshot()        # → 截图成功
mcp_desktop_click(x=500, y=500) # → Clicked
```

---

## 使用示例

### 完整闭环：QQ 发送消息（中文版）

```python
# [准备工作] 安装 pyperclip（Windows 端）
# cmd.exe /c "D:\新建文件夹\python.exe -m pip install pyperclip"

# 1. 截图
mcp_desktop_screenshot(format="jpeg")

# 2. 视觉分析 (配合 Vision 模型)
vision_analyze(screenshot, "找到输入框位置")

# 3. 点击输入框
mcp_desktop_click(x=100, y=200)

# 4. 【中文输入】pyperclip 复制 + Ctrl+V 粘贴（非 type_text）
terminal(command='D:\\新建文件夹\\python.exe -c "import pyperclip; pyperclip.copy(\\'你好，这是RPA自动发送的中文消息\\')"')
mcp_desktop_key_press("ctrl+v")

# 5. 截图确认输入
mcp_desktop_screenshot(format="jpeg")

# 6. 点击发送
mcp_desktop_click(x=300, y=400)

# 7. 截图验证发送结果
mcp_desktop_screenshot(format="jpeg")
```

> ⚠️ **中文输入注意事项**:
> `mcp_desktop_type_text()` 通过键盘事件模拟输入，对中文支持不佳。
> **已验证方案**: Windows Python (pyperclip) 写入剪贴板 → Ctrl+V 粘贴 → 中文正确显示。
> 详见 `scripts/chinese_input.py` 和 `scripts/rpa_daemon.py` 中的 `type_cn()` 方法。

> 另见 `scripts/rpa_daemon.py` — 可直接通过 TCP 连接 daemon 的 Python 客户端库。

### OCR 文字提取（替代视觉模型读字）

视觉模型（Kimi-K2.6、GPT-4o 等）善于理解 UI 布局，但读小字经常**幻视**（凭空虚构文字）。
使用 Tesseract + OpenCV 预处理精确提取文字，绝不幻视。

```bash
# 标准用法（Otsu 阈值，推荐）
python3 scripts/ocr_helper.py 截图.jpg

# 裁剪特定区域后 OCR
python3 scripts/ocr_helper.py 截图.jpg --crop 100 200 400 300

# JSON 格式输出（含置信度）
python3 scripts/ocr_helper.py 截图.jpg --json
```

**推荐工作流**：
```
1. mcp_desktop_screenshot_region(x, y, w, h)   # 截取目标文字区域
2. python3 scripts/ocr_helper.py 区域截图.jpg    # OCR 提取文字
3. LLM 基于 OCR 结果做理解和判断                  # 不是看图！
```

**QQ 聊天窗口坐标参考**：聊天区域 `(212, 12, 250, 790)` ← MCP 1366×853 坐标系

详见 `docs/setup-guide.md` 的「视觉模型幻视」章节和 `scripts/ocr_helper.py`。

### 手动操控

```python
from rpa_daemon import DaemonClient

d = DaemonClient()
d.screenshot("/tmp/desktop.jpg")
d.click(500, 500)
d.type_text("Hello RPA!")
print(d.foreground_window())
```

---

## 关键参数

| 参数 | 值 | 说明 |
|------|-----|------|
| MCP 坐标空间 | 1366×853 | 降采样后的统一坐标系，所有 MCP 工具使用此坐标 |
| 原始分辨率 | 2560×1600 | Daemon 直连的原始物理分辨率 |
| DPI 缩放 | 1.5x | Windows 显示缩放 |
| Daemon 端口 | TCP 19542 | 二进制长度前缀 + JSON 协议 |
| MCP 传输 | stdio | 通过 Hermes Native MCP Client |
| 截图格式 | JPEG quality 70 | ~80-170KB per screenshot |
| 工具数量 | 21 | 13 个桌面操控 + 8 个系统工具 |

---

## 测试结果

### 已通过测试 (2026-06-03)

| 测试项 | 结果 |
|--------|------|
| MCP 握手 & 工具发现 | ✅ 21 tools, 885ms |
| 平台检测 | ✅ wsl2, backend_available |
| 全屏截图 | ✅ 1366×853 JPEG |
| 区域截图 | ✅ |
| 鼠标移动 | ✅ |
| 鼠标左键 | ✅ |
| 键盘输入 (英文) | ✅ type_text |
| 中文输入 (type_text) | ❌ 中文乱码/不显示 |
| 中文输入 (剪贴板方案) | ✅ pyperclip + Ctrl+V，7轮验证通过 |
| 按键 (Enter) | ✅ |

### 端到端验证: QQ 发送消息

```
1. 截图 → 视觉识别 QQ 界面         ✅
2. 定位输入框 → click              ✅
3. 中文输入方案（pyperclip+Ctrl+V） ✅ (7轮跨平台测试验证通过)
4. 截图确认输入                    ✅
5. 点击"发送"按钮                  ✅
6. 截图确认消息已发送              ✅
```

> 📝 中文输入测试摘要:
> - `type_text()` 直接键盘模拟 → 中文乱码
> - `clip.exe` (WSL) 剪贴板 → 编码错误
> - `mcp_desktop_clipboard(paste)` → utf-8 解码失败
> - ✅ **最终方案**: Windows Python pyperclip.copy() → Ctrl+V 粘贴 → 中文完全正确

---

## 视觉模型配置

如果当前模型不支持视觉（如 DeepSeek, GPT 纯文本），需单独配置辅助视觉模型：

```bash
hermes config set auxiliary.vision.provider "custom:<你的提供商>"
hermes config set auxiliary.vision.model "kimi-k2.6"
hermes config set auxiliary.vision.base_url "https://your-api-endpoint/v1"
```

推荐视觉模型：
- **Kimi-K2.6** — 中文 UI 识别优秀，价格低
- **Qwen2.5-VL** — ¥1.6/千张图，性价比极高
- **GPT-4o** — 通用识别最强
- **Claude Sonnet 4** — UI 元素理解精准

---

## 项目文件

```
hermes-windows-rpa/
├── README.md                      # 本文件
├── LICENSE                        # MIT
├── .gitignore
├── scripts/
│   ├── rpa_daemon.py              # Daemon 直连 Python 客户端
│   ├── chinese_input.py           # 中文输入辅助脚本
│   ├── ocr_helper.py              # OCR 文字提取（Otsu 阈值）
│   ├── rpa_ocr_flow.py            # OCR 工作流集成脚本
│   └── qq_auto_sender.py          # QQ 自动发消息示例
├── config/
│   └── hermes-mcp-config.yaml     # Hermes MCP 配置示例
├── docs/
│   ├── architecture.md            # 架构详解
│   ├── setup-guide.md             # 安装指南
│   └── testing.md                 # 测试报告
└── screenshots/                   # 截图样例

```

---

## 参考

- [Hermes Agent](https://github.com/NousResearch/hermes-agent)
- [vadgr-computer-use](https://github.com/MONTBRAIN/vadgr-computer-use)
- [MCP Protocol](https://modelcontextprotocol.io)
