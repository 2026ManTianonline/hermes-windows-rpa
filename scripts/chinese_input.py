#!/usr/bin/env python3
"""Hermes Windows RPA — 中文输入辅助脚本

通过 Windows Python (pyperclip) + Ctrl+V 实现可靠的中文/多语言文本输入。
"""

import subprocess
import sys

# 在此设置 Windows Python 的路径
# 如果路径不同，运行前修改此处
WINDOWS_PYTHON = r"D:\新建文件夹\python.exe"


def check_pyperclip():
    """检查 Windows Python 是否已安装 pyperclip。"""
    cmd = f'"{WINDOWS_PYTHON}" -c "import pyperclip; print(1)"'
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    if result.returncode != 0:
        print("❌ Windows Python 未安装 pyperclip。请运行：")
        print(f'   cmd.exe /c "{WINDOWS_PYTHON} -m pip install pyperclip"')
        return False
    return True


def copy_to_clipboard(text: str) -> bool:
    """将文本复制到 Windows 剪贴板（通过 Windows Python 的 pyperclip）。

    参数:
        text: 要复制的文本（支持中文、英文、符号等任意 Unicode 字符）

    返回:
        True 成功 / False 失败

    用法（在 Hermes 会话中配合 MCP 工具）:
        >>> terminal(command='.../python.exe copy_to_clipboard.py "你好世界"')

        或者手动两步:
        1. 在 WSL 中调用: windows-python chinese_input.py copy "你的文本"
        2. 在 Hermes 中: mcp_desktop_click(x, y)
        3. 粘贴: mcp_desktop_key_press("ctrl+v")
    """
    script = f"""
import pyperclip
text = {repr(text)}
pyperclip.copy(text)
read_back = pyperclip.paste()
if read_back == text:
    print("CLIPBOARD_OK")
else:
    print(f"CLIPBOARD_FAIL: {{repr(read_back)}}")
    sys.exit(1)
"""
    cmd = f'"{WINDOWS_PYTHON}" -c "{script}"'
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    out = result.stdout.strip()
    err = result.stderr.strip()
    if "CLIPBOARD_OK" in out:
        print(f"✅ 已复制到剪贴板 ({len(text)} 字符)")
        return True
    else:
        print(f"❌ 复制失败: {out} {err}")
        return False


def main():
    """命令行入口。"""
    if len(sys.argv) < 2:
        print("用法:")
        print("  python chinese_input.py check           # 检查 pyperclip 是否就绪")
        print('  python chinese_input.py copy "你的文本"  # 将文本复制到剪贴板')
        return

    if sys.argv[1] == "check":
        if check_pyperclip():
            print("✅ 环境就绪，可以使用中文输入功能")
        return

    if sys.argv[1] == "copy":
        text = sys.argv[2] if len(sys.argv) > 2 else "测试中英输入qazwsx？。，/.,m"
        if not check_pyperclip():
            return
        copy_to_clipboard(text)
        return

    print(f"未知命令: {sys.argv[1]}")


if __name__ == "__main__":
    main()
