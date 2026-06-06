# 架构详解

## 系统架构

```
┌──────────────────────────────────────────────────────────────────┐
│  WSL2 (Ubuntu)                                                    │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  Hermes Agent                                                 │  │
│  │                                                               │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │  Native MCP Client                                       │  │  │
│  │  │                                                          │  │  │
│  │  │  tools/call:                                             │  │  │
│  │  │  ├─ {"name": "screenshot",     "arguments": {}}          │  │  │
│  │  │  ├─ {"name": "click",          "arguments": {x,y}}       │  │  │
│  │  │  ├─ {"name": "type_text",      "arguments": {text}}      │  │  │
│  │  │  ├─ {"name": "get_screen_size","arguments": {}}          │  │  │
│  │  │  └─ ... (21 tools total)                                  │  │  │
│  │  └──────────────────┬──────────────────────────────────────┘  │  │
│  │                     │ stdio (stdin/stdout)                     │  │
│  └─────────────────────┼─────────────────────────────────────────┘  │
│                        │                                            │
│  ┌─────────────────────┴─────────────────────────────────────────┐  │
│  │  vadgr-cua (vadgr-computer-use v0.3.0)                        │  │
│  │                                                               │  │
│  │  MCP 服务器进程, 通过 stdio 接收 JSON-RPC 请求                 │  │
│  │                                                               │  │
│  │  初始化协议:                                                   │  │
│  │  1. initialize → 协议版本协商                                   │  │
│  │  2. notifications/initialized → 就绪                           │  │
│  │  3. tools/list → 获取工具列表                                   │  │
│  │  4. tools/call → 调用具体工具                                   │  │
│  │                                                               │  │
│  │  工具分层:                                                     │  │
│  │  Tier 0 (8 tools): fs, shell, http, env, time, tempfile,      │  │
│  │                    data, clipboard                             │  │
│  │  Tier 2 (13 tools): screenshot, click, type_text, scroll,      │  │
│  │                    key_press, move_mouse, drag, ...             │  │
│  └─────────────────────┬─────────────────────────────────────────┘  │
│                        │ TCP localhost:19542                         │
└────────────────────────┼─────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│  Windows 桥接守护进程 (daemon.py)                                  │
│                                                                    │
│  协议: 4 字节大端长度前缀 + JSON 载荷                               │
│                                                                    │
│  方法列表:                                                         │
│  ├─ ping              → 心跳检测                                   │
│  ├─ screenshot_full   → 全屏截图 (参数: quality)                   │
│  ├─ screenshot_region → 区域截图                                   │
│  ├─ screen_size       → 屏幕尺寸 (2560×1600)                      │
│  ├─ scale_factor      → DPI 缩放 (1.5x)                           │
│  ├─ foreground_window → 前台窗口信息                               │
│  ├─ click             → 鼠标左键点击                               │
│  ├─ double_click      → 鼠标双击                                   │
│  ├─ right_click       → 鼠标右键                                   │
│  ├─ move_mouse        → 移动鼠标                                   │
│  ├─ type_text         → 键盘输入                                   │
│  ├─ key_press         → 按键组合                                   │
│  ├─ scroll            → 滚动滚轮                                   │
│  └─ drag              → 拖拽                                       │
│                                                                    │
│  依赖:                                                             │
│  ├─ mss 10.2.0       → 截图 (DirectX / Desktop Duplication API)   │
│  └─ pyautogui / Win32 → 鼠标键盘 (SendInput)                      │
└──────────────────────────────────────────────────────────────────┘
```

## 坐标系统

架构中存在 **两套坐标系统**，理解它们的区别很重要：

### MCP 坐标空间 (1366×853)

- 所有 MCP 工具（`screenshot`, `click`, `move_mouse` 等）使用此坐标
- 由 vadgr-cua 自动降采样：原始 2560×1600 → MCP 1366×853
- **以 MCP 截图为准**：截图尺寸就是坐标空间尺寸
- 鼠标操作会自动从 MCP 坐标映射回真实屏幕坐标

### 原始坐标空间 (2560×1600)

- Daemon 直连（TCP:19542）使用原始物理分辨率
- 调用 `screenshot_full` 返回 2560×1600 图像
- 只有绕过 MCP、直接连接 daemon 时才使用此坐标

### 使用规则

```
MCP 通道: 坐标范围 0-1366 x 0-853
Daemon 直连: 坐标范围 0-2560 x 0-1600

首次截图 → 读取截图尺寸 → 在该坐标系内操作
```

## 数据流

### 完整 RPA 闭环

```
[观察]         screenshot()        获取桌面截图 (1366×853 JPEG)
    │
    ▼
[理解]         vision_analyze()    视觉模型分析 UI 元素及坐标
    │
    ▼
[决策]         判断下一步操作      点击/输入/滚动等
    │
    ▼
[执行]         click(x,y)          在 MCP 坐标空间内操作
    │
    ▼
[验证]         screenshot()        再次截图确认操作结果
    │
    ▼
              (循环)
```

### 写操作 (click/type) 的安全原则

1. **先截图，再点击** — 永远基于最新截图定位
2. **先确认，再动作** — 视觉确认目标存在再操作
3. **点完截图验证** — 每次操作后截图确认结果

### 中文输入方案（pyperclip + Ctrl+V）

标准 `type_text()` 使用键盘事件模拟，对中文等非 ASCII 字符支持不佳。
**已验证的可靠方案** 是通过 WSL 调用 Windows Python 的 pyperclip 写入
系统剪贴板，然后发送 Ctrl+V 粘贴：

```
数据流:
  Hermes Agent (WSL)
    → terminal() 调用 D:\新建文件夹\python.exe
    → pyperclip.copy("中文消息")          # Windows 原生剪贴板写入
    → mcp_desktop_click(x, y)             # 点击目标输入框
    → mcp_desktop_key_press("ctrl+v")     # 粘贴中文内容
    → mcp_desktop_screenshot()            # 截图验证

原因:
  - WSL 的 clip.exe / clip.exe 使用 GBK 编码，中文会乱码
  - MCP clipboard 工具的 paste() 使用 UTF-8 解码，与 clip.exe 输出不匹配
  - Windows Python (pyperclip) 直接调用 Win32 剪贴板 API，编码正确
```

详见 `scripts/chinese_input.py` 和 `scripts/rpa_daemon.py` 的 `type_cn()` 方法。

## MCP 协议细节

### D 正确的工具调用格式

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "screenshot",
    "arguments": {
      "format": "jpeg"
    }
  }
}
```

### 错误的调用格式 (会导致 32602 错误)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "screenshot"
}
```

## WeChat 布局公式架构 (2026-06-06)

WeChat 4.x (Qt) 不暴露 UIA 控件，无法用 pywinauto/wxauto 获取内部元素。
有效方案：**pygetwindow 定位窗口 → 固定公式反推所有 UI 坐标**。

### 布局常量

```
LEFTBAR_W = 60       # 左侧导航栏（固定像素）
TITLEBAR_H = 50      # 顶部标题栏
CONTACT_ITEM_H = 64  # 每个联系人条目高度
INPUT_H = 60         # 输入框区域高度
SEND_BTN_W = 50      # 发送按钮宽度
LIST_W = 240~400     # 会话列表宽度（窗口宽度的 33%，钳位）
```

### 坐标公式

```python
# 设窗口左=lx, 上=ty, 宽=w, 高=h
chat_x = lx + LEFTBAR_W + LIST_W
chat_w = w - LEFTBAR_W - LIST_W

搜索框   = (lx+LBF_W+8,   ty+8,            LIST_W-16, 38)
输入框   = (chat_x+8,     ty+h-68,         chat_w-70, 50)
发送按钮 = (lx+w-62,      ty+h-54,         50,        34)
聊天区   = (chat_x,       ty+50,           chat_w,    h-110)
会话列表 = (lx+LBF_W,     ty+50,           LIST_W,    h-50)
```

### 搜索框优先策略

不点击联系人列表（列表随新消息置顶，顺序不稳定），而是：
1. 点击搜索框（固定坐标）
2. 粘贴群名（pyperclip + Ctrl+V）
3. Enter → 打开指定会话

### 校准一次，永久使用

```python
import pygetwindow as gw, json
wx = gw.getWindowsWithTitle("微信")[0]
calib = {"left": wx.left, "top": wx.top, "width": wx.width, "height": wx.height}
json.dump(calib, open("wx_calib.json", "w"))
# 窗口不移位，永久复用
```

### 数据流

```python
pygetwindow         # 获取窗口坐标 (30ms)
  → 公式反推         # 计算所有 UI 坐标 (0ms)
    → 点击搜索框      # 固定坐标，不受列表顺序影响
      → 粘贴群名     # pyperclip + Ctrl+V
        → Enter     # 打开会话
          → 粘贴内容 # pyperclip + Ctrl+V
            → 发送  # 点击发送按钮
```

### 优势

| 对比项 | vision 方案 | 布局公式方案 |
|--------|-----------|------------|
| 耗时 | 3-5s/步 | <50ms/步 |
| 成本 | 每次 vision API 费用 | 0 |
| 可靠性 | 依赖模型识别精度 | 100%（坐标固定） |
| 列表顺序 | 必须 OCR 读 | 搜索框不受影响 |

---

## 安全边界

| 层级 | 保护措施 |
|------|----------|
| Hermes Agent | YOLO 模式开关, 危险命令审批 |
| MCP Server | Tier 分级 (ReadOnly / Medium / High) |
| Daemon | 仅监听 127.0.0.1, 无外部暴露 |
| Windows | 需用户手动启动 daemon |
