# 测试报告

> 测试日期: 2026-06-03  
> 环境: Windows 11 24H2 + WSL2 (Ubuntu)  
> Hermes Agent v0.15.1, vadgr-computer-use v0.3.0

---

## 1. 基础架构测试

### 1.1 Windows 桥接守护进程

| 测试项 | 结果 | 说明 |
|--------|------|------|
| Daemon 进程 | ✅ PID 27352 | 监听 0.0.0.0:19542 |
| Ping 心跳 | ✅ | pong + version_hash |
| 全屏截图 | ✅ 2560×1600 | JPEG, 428KB, mss 直连 |
| 屏幕尺寸 | ✅ 2560×1600 | 原生分辨率 |
| DPI 缩放 | ✅ 1.5x | Windows 缩放因子 |
| 前台窗口 | ✅ | 正确识别当前活动窗口 |
| 鼠标点击 | ✅ | click(100,100) |
| 键盘输入 | ✅ | type_text |
| 鼠标移动 | ✅ | move_mouse |

### 1.2 MCP 服务器

| 测试项 | 结果 | 说明 |
|--------|------|------|
| 连接握手 | ✅ 885ms | initialize + tools/list |
| 工具发现 | ✅ 21 tools | 13 Tier2 + 8 Tier0 |
| 平台检测 | ✅ wsl2 | get_platform |
| 截图 | ✅ 1366×853 | 降采样后 JPEG, ~167KB |
| 区域截图 | ✅ | screenshot_region |
| 鼠标移动 | ✅ | move_mouse(1000, 120) |
| 鼠标左键 | ✅ | click(500, 500) |
| 键盘输入 | ✅ | type_text("RPA_Test_OK") |
| 按键 | ✅ | key_press("enter") |
| 屏幕尺寸 | ✅ 1366×853 | MCP 坐标空间 |

---

## 2. 端到端场景测试：QQ 发送消息

### 2.1 测试流程

```
1. 截图识别 QQ 界面     → mcp_desktop_screenshot()
2. 定位输入框           → vision_analyze()
3. 点击输入框           → mcp_desktop_click(x, y)
4. 输入内容             → Windows pyperclip.copy() + Ctrl+V 粘贴
5. 截图确认输入         → mcp_desktop_screenshot()
6. 点击发送按钮         → mcp_desktop_click(x, y)
7. 截图验证发送结果     → mcp_desktop_screenshot()
```

### 2.2 测试结果

| 步骤 | 结果 | 备注 |
|------|------|------|
| 1. 截图 | ✅ | 1386×853, 桌面完整可见 |
| 2. 视觉识别 | ✅ | 识别到 QQ 会话窗口及输入框 |
| 3. 点击输入框 | ✅ | 光标定位成功 |
| 4. 输入文字 (剪贴板方案) | ✅ | pyperclip.copy() → Ctrl+V, 中文正确 |
| 5. 截图确认 | ✅ | 输入框内容正确 |
| 6. 点击发送 | ✅ | 消息已发送 |
| 7. 截图验证 | ✅ | 聊天记录出现新消息 |

### 2.3 测试截图

| 阶段 | 截图 | 说明 |
|------|------|------|
| 输入后 | ![输入截图](../screenshots/img_7b8b5c004e63.jpg) | 输入框显示 "1111111" |
| 发送后 | ![发送截图](../screenshots/img_3892d9544e07.jpg) | 消息已发送到"我的手机" |

---

## 3. 中文输入专项测试

### 3.1 背景

MCP 的 `type_text()` 通过键盘事件模拟按键，对 ASCII 英文支持正常，
但对中文等 Unicode 多字节字符支持不佳（不同应用程序的 IME 处理各不相同）。

### 3.2 测试过程（7轮）

| 轮次 | 方法 | 结果 | 说明 |
|------|------|------|------|
| 1 | `mcp_desktop_type_text(text)` | ❌ | 中文显示为乱码 |
| 2 | `mcp_desktop_clipboard(copy)` + `ctrl+v` | ❌ | clip.exe 编码问题 |
| 3 | 同上，换 pyperclip 设剪贴板 | ❌ | WSL 终端显示乱码（终端编码问题） |
| 4 | Windows Python pyperclip → ctrl+v | ❌ | 粘贴到输入框后乱码 |
| 5 | Windows Python pyperclip.copy() (已验证 Text OK) + ctrl+v | ❌ | repr() 错误显示（实际内容正确） |
| 6 | 直接 pyperclip 设剪贴板 (CLIPBOARD_OK) + ctrl+v | ✅ | 中文正确显示 |
| 7 | 跨平台输入框再测一轮 | ✅ | **中文完全正确** |

### 3.3 最终方案

```
Windows Python (D:\新建文件夹\python.exe)
  → pyperclip.copy("中文消息")    # 写入系统剪贴板，验证 CLIPBOARD_OK
  → mcp_desktop_click(x, y)       # 点击输入框
  → mcp_desktop_key_press("ctrl+v")  # 粘贴
  → mcp_desktop_screenshot()      # 截图验证
```

### 3.4 关键发现

1. **`mcp_desktop_type_text()`** 对中文支持不佳 — 这是键盘事件模拟的固有限制
2. **`mcp_desktop_clipboard`** 内部使用 WSL 的 clip.exe，存在 GBK/UTF-8 编码不匹配
3. **Windows Python 的 pyperclip** 是唯一正确方案 — 因为它在 Windows 原生环境下运行，直接调用 Win32 剪贴板 API
4. 在 WSL 终端中看到的 repr() 显示为乱码是**终端编码问题**，不是剪贴板内容问题。验证方法：`if pyperclip.paste() == text: print("CLIPBOARD_OK")`
5. 该方案不限于 QQ，适用于**任何 Windows 应用程序的输入框**

### 3.5 测试文本

```
测试中英输入qazwsx？。，/.,m
```

---

## 4. 坐标系统验证（重编号）

### MCP 坐标空间 (1366×853)

所有 MCP 工具使用降采样后的坐标空间：

```
原始 2560×1600 → 降采样 → 1366×853 (MCP 截图尺寸)
```

**重要**: 不要在 MCP 截图和 daemon 截图之间混用坐标——它们属于不同的坐标系。

### 坐标映射

```
MCP click(x, y) → 自动映射 → 真实屏幕坐标
MCP screenshot() → 返回 1366×853 图像 → 坐标以该图像为准
Daemon screenshot_full() → 返回 2560×1600 图像 → 坐标以该图像为准
```

---

## 4. 已知问题

### 4.1 hermes mcp test 超时

**现象**: `hermes mcp test desktop` 偶尔报 Connection failed

**根因**: args 配置格式错误时会导致 MCP 进程启动失败。修复后仍可能有偶发超时

**不影响实际使用**, 进入 Hermes 会话后 MCP 工具正常工作

### 4.2 cwd 参数问题

**现象**: `mcp_desktop_shell` 传入空 cwd 时报错

**报错**: `[Errno 2] No such file or directory: ''`

**不影响核心 RPA 功能**（screenshot/click/type 均不依赖此工具）

### 4.3 SSE 传输不可用

vadgr-computer-use 的 SSE 模式在当前版本下无响应。建议使用 stdio 模式。

---

## 5. 性能指标

| 操作 | 耗时 | 说明 |
|------|------|------|
| MCP 连接握手 | ~885ms | 首次连接 |
| 全屏截图 (MCP) | ~200ms | 含降采样和 JPEG 编码 |
| 全屏截图 (Daemon) | ~50ms | 原生 mss 截图 |
| 鼠标点击 | ~30ms | Win32 SendInput |
| 键盘输入 | ~10ms/字符 | 模拟按键 |
