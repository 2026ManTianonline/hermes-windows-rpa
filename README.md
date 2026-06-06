# Hermes Windows RPA

> 基于 Hermes Agent 的 Windows 桌面 UI 自动化方案  
> 截图 → 视觉识别 → MCP 执行 → 循环验证 的完整 RPA 闭环  
> 可实现微信群聊、QQ群聊等桌面应用自动化交互  
> WSL + Hermes Agent → Windows 桌面：截图、视觉识别、OCR、MCP 执行、闭环验证
---

## 快速导航

| 文档 | 用途 |
|------|------|
| [README.md](README.md) （本文件） | 项目总览、快速开始、文件清单 |
| [docs/setup-guide.md](docs/setup-guide.md) | 完整安装步骤、常见问题 |
| [docs/architecture.md](docs/architecture.md) | 架构详解、协议、坐标系统 |
| [docs/testing.md](docs/testing.md) | 测试结果、性能指标 |

---

## 项目简介

本项目实现了一套运行在 **WSL (Ubuntu) + Hermes Agent** 环境下的 Windows 桌面 RPA 方案。
通过多种互补技术，覆盖从简单鼠标点击到复杂中文 UI 交互的全场景：

| 层 | 技术 | 场景 |
|----|------|------|
| 🖥️ 基础操控 | MCP 桌面工具（vadgr-computer-use） | 截图、点击、键盘、滚动 |
| 👁️ 视觉理解 | Vision 模型（Kimi/GPT/Qwen） | 定位 UI 元素位置 |
| 📝 文字提取 | **EasyOCR** + Tesseract | 精确读中文字（不幻视） |
| 📐 布局公式 | pygetwindow + 坐标反推 | **0 成本**获取全部 UI 坐标 |
| ⌨️ 中文输入 | Windows Python pyperclip + Ctrl+V | **唯一可靠**的中文输入方案 |

### 核心优化成果

| 优化 | 改进前 | 改进后 | 节省 |
|------|--------|--------|------|
| **WeChat 布局公式** | 每步调视觉模型（~3s/次） | pygetwindow → 公式反推（0ms） | 无限次 vision 调用 |
| **EasyOCR 中文输出** | terminal 管道乱码 | 写 UTF-8 JSON → read_file | 中文正确显示 |
| **搜索框优先策略** | OCR 读联系人列表 → 点击 | 搜索框搜群名 → Enter | 不受列表顺序影响 |
| **Pyperclip 中文输入** | type_text 乱码 | pyperclip.copy + Ctrl+V | 中文完全正确 |
| **校准一次永久使用** | 每次重新定位窗口 | 保存窗口坐标 JSON 复用 | 永久 0 vision |

### 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│  Hermes Agent (WSL)                                          │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Native MCP Client (21 tools)                            │ │
│  │  └─ mcp_desktop_screenshot()    截图                    │ │
│  │  └─ mcp_desktop_click(x, y)     鼠标点击                │ │
│  │  └─ mcp_desktop_type_text(text) 键盘输入（英文）        │ │
│  │  └─ mcp_desktop_key_press()     按键组合                │ │
│  └────────────────────┬────────────────────────────────────┘ │
│                       │ stdio                                │
│  ┌────────────────────┴────────────────────────────────────┐ │
│  │  vadgr-computer-use MCP Server (v0.3.0)                 │ │
│  │  21 tools (screenshot, click, type, scroll, etc.)       │ │
│  │  └─ TCP localhost:19542 (Windows 桥接 daemon)          │ │
│  └────────────────────┬────────────────────────────────────┘ │
│                       │                                      │
│  ┌────────────────────┴────────────────────────────────────┐ │
│  │  工具链 (WSL 端)                                         │ │
│  │  └─ easyocr_reader.py     WSL wrapper → EasyOCR        │ │
│  │  └─ ~/.local/bin/easyocr  快捷命令                     │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Windows 端                                                   │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  vadgr daemon (TCP :19542)                                │ │
│  │  mss 截图 (2560×1600) + Win32 SendInput                  │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Windows Python (D:\新建文件夹\python.exe)                 │ │
│  │  └─ easyocr_runner.py   EasyOCR 引擎                    │ │
│  │  └─ pyperclip           中文剪贴板输入                  │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Windows 桌面程序 (WeChat/QQ/浏览器/Notepad...)          │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| AI Agent | [Hermes Agent](https://hermes-agent.nousresearch.com) | v0.15+ |
| MCP 服务器 | [vadgr-computer-use](https://github.com/MONTBRAIN/vadgr-computer-use) | v0.3.0 (21 tools) |
| 截图引擎 | mss (Windows Desktop Duplication API) | — |
| 鼠标键盘 | Win32 SendInput | — |
| OCR 引擎 | **EasyOCR** (推荐) / Tesseract 5.3.4 | EasyOCR CPU |
| 窗口定位 | pygetwindow | pip install |
| 中文输入 | Windows Python + **pyperclip** + Ctrl+V | 7轮验证通过 ✅ |
| 布局公式 | pygetwindow → 坐标反推 | **0 vision 调用** |
| 视觉模型 | Kimi-K2.6 / GPT-4o / Qwen-VL-Max | 辅助定位用 |
| 运行环境 | Windows 11 + WSL2 (Ubuntu 24.04) | — |

---

## 快速开始

### 前置条件

- Windows 11 24H2+ / Windows 10 22H2+
- WSL2 已启用 (Ubuntu 22.04/24.04)
- Hermes Agent 已安装

### 1. 安装 MCP 服务器

```bash
python3 -m venv ~/.hermes/venvs/rpa
~/.hermes/venvs/rpa/bin/pip install vadgr-computer-use
~/.hermes/venvs/rpa/bin/vadgr-cua doctor   # 验证
```

### 2. 配置 Hermes MCP

```bash
hermes mcp add desktop \
  --command ~/.hermes/venvs/rpa/bin/vadgr-cua \
  --args '["--transport","stdio"]'
```

⚠️ 检查 `~/.hermes/config.yaml` 中 args 为 YAML 列表格式（不是字符串）：
```yaml
    args:
      - --transport
      - stdio
```

### 3. 安装 Windows Python 依赖

```bash
cmd.exe /c "D:\新建文件夹\python.exe -m pip install pyperclip easyocr"
```

### 4. 配置工具链

```bash
# 创建 WSL 侧快捷命令
ln -sf /mnt/d/hermes-windows-rpa/scripts/easyocr_reader.py ~/.local/bin/easyocr

# 验证
python3 ~/.local/bin/easyocr 测试截图.jpg | python3 -c "import sys,json; print(f'{len(json.load(sys.stdin))} items')"
```

### 5. 验证完整链路

```bash
# 在 Hermes 会话中
mcp_desktop_get_screen_size()   # → 1366x853
mcp_desktop_screenshot()        # → 截图成功
```

---

## 使用场景

### 场景 A：读微信/QQ 聊天区文字

**最优路径（0 vision 调用）：**

```python
# 1. 截图聊天区域
mcp_desktop_screenshot_region(x=360, y=157, width=444, height=577)

# 2. EasyOCR 读文字（中文正确）
terminal("python3 ~/.local/bin/easyocr /home/h/.hermes/image_cache/img_xxx.jpg")

# 3. LLM 基于 OCR 结果做判断
```

### 场景 B：微信发送中文消息

**最优路径（0 vision 调用，布局公式）：**

```python
# 1. 获取窗口坐标（校准一次，永久复用）
# pygetwindow → (52,107) 752x697

# 2. 公式反推所有 UI 坐标
#   搜索框: (120,115) 232x38
#   输入框: (368,736) 370x50
#   发送按钮: (742,740) 50x34

# 3. 搜群名（搜索框优先策略，不受列表顺序影响）
mcp_desktop_click(x=236, y=134)                    # 点击搜索框
/mnt/d/新建文件夹/python.exe -c "import pyperclip; pyperclip.copy('目标群名')"  # 复制群名
mcp_desktop_key_press("ctrl+v")                    # 粘贴
mcp_desktop_key_press("enter")                     # 确认

# 4. 输入中文消息
mcp_desktop_click(x=553, y=761)                    # 点击输入框
/mnt/d/新建文件夹/python.exe -c "import pyperclip; pyperclip.copy('通报内容')"  # 粘贴内容
mcp_desktop_key_press("ctrl+v")                    # 粘贴

# 5. 发送
mcp_desktop_click(x=767, y=757)                    # 点击发送按钮
```

### 场景 C：OCR 读一般桌面文字

```bash
# EasyOCR（推荐，中文准确率 80-99%）
python3 ~/.local/bin/easyocr 截图.jpg | python3 -c "
import sys, json
for d in json.load(sys.stdin):
    if d['conf'] >= 60:
        print(f'{d[\"text\"]} ({d[\"conf\"]}%)')
"

# Tesseract（快，适合英文/大字）
python3 scripts/ocr_helper.py 截图.jpg --json
```

### 场景 D：通用 RPA 闭环

```python
# 1. 截图 → 2. 视觉定位 → 3. 执行 → 4. 截图验证
mcp_desktop_screenshot()
# vision_analyze → click(x,y)
# Windows pyperclip + Ctrl+V (中文)
# click(x,y) 发送
mcp_desktop_screenshot()  # 验证
```

---

## ⚠️ 关键陷阱

### 中文输入：只有 pyperclip + Ctrl+V 可用

| 方案 | 结果 | 原因 |
|------|------|------|
| `mcp_desktop_type_text()` | ❌ 乱码 | UTF-8 → GBK 编码错位 |
| `mcp_desktop_clipboard(copy)` | ❌ 乱码 | clip.exe 编码问题 |
| **Windows pyperclip + Ctrl+V** | ✅ **正确** | Win32 原生剪贴板 API |

### EasyOCR 中文输出：不能走 terminal 管道

| 方式 | 结果 |
|------|------|
| terminal("... easyocr ...") 直接读 stdout | ❌ 中文乱码 |
| **easyocr_reader.py 写 JSON 文件 → read_file** | ✅ 中文正确 |

详见 `scripts/easyocr_runner.py` 和 `scripts/easyocr_reader.py`。

---

## 项目文件

```
hermes-windows-rpa/
├── README.md                        # 本文件
├── LICENSE                          # MIT
├── .gitignore
├── scripts/
│   ├── easyocr_runner.py            # EasyOCR 引擎（Windows 端执行）
│   ├── easyocr_reader.py            # EasyOCR WSL 封装（~/.local/bin/easyocr）
│   ├── rpa_daemon.py                # Daemon 直连 Python 客户端（含 type_cn()）
│   ├── chinese_input.py             # 中文输入辅助脚本
│   ├── ocr_helper.py                # Tesseract OCR 文字提取
│   ├── rpa_ocr_flow.py              # OCR 工作流集成
│   └── qq_auto_sender.py            # QQ 自动发送示例
├── config/
│   └── hermes-mcp-config.yaml       # Hermes MCP 配置示例
├── docs/
│   ├── architecture.md              # 架构详解 & 坐标系统
│   ├── setup-guide.md               # 安装指南 & FAQ
│   └── testing.md                   # 测试报告
└── screenshots/                     # 截图样例（gitignored 自动生成）
    └── README.md
```

---

## 版本历史

| 日期 | 变更 |
|------|------|
| 2026-06-06 | 新增 EasyOCR 中文输出工具、WSL wrapper |
| 2026-06-06 | 验证 WeChat 布局公式、搜索框优先策略 |
| 2026-06-03 | 初始版本：MCP 搭建、中文输入 7 轮验证、QQ 端到端测试 |

---

## 参考

- [Hermes Agent](https://github.com/NousResearch/hermes-agent)
- [vadgr-computer-use](https://github.com/MONTBRAIN/vadgr-computer-use)
- [MCP Protocol](https://modelcontextprotocol.io)
