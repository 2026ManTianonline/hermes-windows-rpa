# 安装指南

## 环境要求

| 组件 | 要求 | 验证 |
|------|------|------|
| Windows | 11 24H2 或 10 22H2+ | `winver` |
| WSL | WSL2 + Ubuntu 22.04/24.04 | `wsl --status` |
| Python (WSL) | 3.10+ | `python3 --version` |
| Python (Windows) | 3.10+ | `python --version` |
| Hermes Agent | v0.14.0+ | `hermes --version` |

## 完整安装步骤

### 步骤 1：创建虚拟环境

```bash
python3 -m venv ~/.hermes/venvs/rpa
```

### 步骤 2：安装 MCP 服务器

```bash
~/.hermes/venvs/rpa/bin/pip install vadgr-computer-use

# 验证安装
~/.hermes/venvs/rpa/bin/vadgr-cua doctor
```

预期输出：
```json
{
  "daemon_running": false,
  "registry_loaded": true,
  "tool_count": 21
}
```

### 步骤 3：配置 Hermes MCP

```bash
hermes mcp add desktop \
  --command ~/.hermes/venvs/rpa/bin/vadgr-cua \
  --args '["--transport","stdio"]'
```

#### 重要：验证 args 格式

检查 `~/.hermes/config.yaml` 中 MCP 配置的格式：

```yaml
# ✅ 正确格式 (YAML 列表)
mcp_servers:
  desktop:
    command: /home/h/.hermes/venvs/rpa/bin/vadgr-cua
    args:
      - --transport
      - stdio
    enabled: true
```

```yaml
# ❌ 错误格式 (单个字符串)
    args: '["--transport","stdio"]'
```

如果格式错误，用以下命令修复：

```bash
# 使用 Python 修复 YAML
python3 -c "
import yaml
with open('/home/h/.hermes/config.yaml','r') as f:
    data = yaml.safe_load(f)
data['mcp_servers']['desktop']['args'] = ['--transport','stdio']
with open('/home/h/.hermes/config.yaml','w') as f:
    yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
"
```

### 步骤 4：配置辅助视觉模型（可选）

如果当前模型不支持视觉（如 DeepSeek, GPT 纯文本），需单独配置：

```bash
# 获取你的提供商 API key
export VISION_API_KEY="your-key"

# 设置辅助视觉
hermes config set auxiliary.vision.provider "custom:你的提供商名称"
hermes config set auxiliary.vision.model "kimi-k2.6"
hermes config set auxiliary.vision.base_url "https://your-api-endpoint/v1"
hermes config set auxiliary.vision.api_key "$VISION_API_KEY"
```

### 步骤 5：安装 Windows 桥接守护进程

#### 自动部署

```bash
~/.hermes/venvs/rpa/bin/vadgr-cua install-daemon
```

如果自动部署失败（Windows Python 不在标准路径），按以下手动方式：

#### 手动部署

```bash
# 1. 在 Windows 端安装依赖
cmd.exe /c "python -m pip install mss pyautogui pillow"

# 2. 创建 daemon 目录
cmd.exe /c "mkdir C:\Users\%USERNAME%\vadgr"

# 3. 复制 daemon.py（从 vadgr-computer-use 包中）
# 找到源文件路径：
python3 -c "import computer_use.bridge.daemon; print(computer_use.bridge.daemon.__file__)"

# 4. 手动启动
cmd.exe /c "start /B python C:\Users\<用户名>\vadgr\daemon.py --port 19542"
```

### 步骤 6：验证完整链路

```bash
# 1. 确认 daemon 运行
cmd.exe /c "netstat -ano | findstr :19542"
# 输出: TCP 0.0.0.0:19542 LISTENING <PID>

# 2. 确认 MCP 连接
hermes mcp test desktop
# 输出: ✓ Connected (...ms)
#       ✓ Tools discovered: 21

# 3. 使用 MCP 工具
hermes chat -q "屏幕尺寸是多少？"
# 在会话中调用 mcp_desktop_get_screen_size()
```

## 常见问题

### Daemon 启动后截图失败

**现象**: daemon 运行中但截图返回空

**原因**: Windows Python 缺少 mss 库

**解决**:
```bash
cmd.exe /c "python -m pip install mss"
```

### MCP 工具返回 "Invalid request parameters"

**原因**: 使用了错误的 JSON-RPC 格式

**正确格式**:
```json
{"method": "tools/call", "params": {"name": "screenshot", "arguments": {"format": "jpeg"}}}
```

**错误格式**:
```json
{"method": "screenshot"}
```

### Python 版本不兼容

如果 Windows Python 3.14+ 下 pyautogui 截图失败：

```bash
cmd.exe /c "python -m pip install pillow --upgrade"
```

### 中文输入乱码或不显示

`type_text` 通过键盘事件模拟输入，中文可能不生效。

**背景**: 经过 7 轮测试验证，发现 MCP 的 `type_text()` 和 `clipboard` 工具对中文支持不佳（键盘事件模拟和 clip.exe 编码问题）。

**解决方案（已验证通过）**:

```bash
# 1. 安装依赖（Windows 端）
cmd.exe /c "D:\新建文件夹\python.exe -m pip install pyperclip"

# 2. 在 Hermes 会话中使用（3 步完成中文输入）
#    第 1 步：Windows Python 写入剪贴板
terminal(command='D:\\新建文件夹\\python.exe -c "import pyperclip; pyperclip.copy(\'你好世界\')"')

#    第 2 步：点击目标输入框
mcp_desktop_click(x=500, y=700)

#    第 3 步：Ctrl+V 粘贴
mcp_desktop_key_press("ctrl+v")

# 4 步：截图验证（可选）
mcp_desktop_screenshot()
```

**验证方式**:
```bash
cmd.exe /c "D:\新建文件夹\python.exe -c "import pyperclip; pyperclip.copy('测试中英输入qazwsx？。，/.,m'); print('CLIPBOARD_OK' if pyperclip.paste() == '测试中英输入qazwsx？。，/.,m' else 'FAIL')""
```

**注意**: WSL 终端显示 pyperclip.paste() 的 repr() 可能看起来是乱码，但这是 WSL 终端编码问题，实际剪贴板内容是正确的。验证方法是用 `CLIPBOARD_OK` 判断。

**自动化脚本**: 见 `scripts/chinese_input.py` 和 `scripts/rpa_daemon.py` 中的 `type_cn()` 方法。

---

### 视觉模型幻视（误读文字）

**现象**: 视觉模型（Kimi-K2.6, GPT-4o 等）在识别屏幕截图中的小字时，经常出现"幻视"——把 "哈喽" 看成 "哈嗖"，把 "发送" 看成 "发浅" 等。

**根因**: 视觉模型擅长理解语义和空间关系，但不擅长精确 OCR（光学字符识别），尤其是小字、中文、带背景的文字。

**解决方案**: 不使用视觉模型读字。改用 **Tesseract OCR + 图像预处理**：

```bash
# OCR 提取文字（精确！不会幻视）
python3 /mnt/d/hermes-windows-rpa/scripts/rpa_ocr_flow.py 截图.jpg

# 如果已知文字区域坐标（可以裁剪以减少干扰）
python3 /mnt/d/hermes-windows-rpa/scripts/rpa_ocr_flow.py 截图.jpg --region x y w h

# JSON 格式（含坐标信息）
python3 /mnt/d/hermes-windows-rpa/scripts/ocr_helper.py 截图.jpg --json
```

**推荐工作流**:
```
1. mcp_desktop_screenshot()                     # 截全屏
2. vision_analyze("找到聊天气泡/文字区域的坐标") # 只找位置，不读字
3. screenshot_region(x, y, w, h)                # 截取该区域（大图更清晰）
4. rpa_ocr_flow.py 区域截图.jpg                  # OCR 提取文字（精确）
5. LLM 基于 OCR 结果做理解（不是看图）            # 消除幻视
```

**脚本列表**:
| 脚本 | 功能 | 适合场景 |
|------|------|----------|
| `scripts/ocr_helper.py` | 基础 OCR，支持 --crop 和 --json | 直接看文字 |
| `scripts/rpa_ocr_flow.py` | 完整工作流 | 全链路 RPA |

**已知限制**:
- Tesseract 对艺术字、倾斜文字、极低分辨率文字识别率下降
- 复杂桌面背景（壁纸、半透明窗口）可能干扰检测
- 如需更高精度，可考虑接入付费 OCR API（百度/阿里云 OCR）
