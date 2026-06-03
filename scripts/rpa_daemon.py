"""Hermes RPA — 直连 Windows 桥接 Daemon 的工具函数

用法：
  from rpa_daemon import DaemonClient
  
  d = DaemonClient()
  info = d.screenshot("/tmp/desktop.jpg")
  d.click(500, 500)
  d.type_text("hello")
  print(d.foreground_window())
"""

import socket
import struct
import json
import base64
import subprocess
import os


# Windows Python 路径（用于中文输入时的 pyperclip 调用）
# 如果路径不同，修改此变量
WINDOWS_PYTHON = os.environ.get(
    "WINDOWS_PYTHON_PATH",
    r"D:\新建文件夹\python.exe"
)


class DaemonClient:
    """直连 Windows 桥接 daemon (TCP:19542) 的客户端。"""

    def __init__(self, host="127.0.0.1", port=19542, timeout=10):
        self.host = host
        self.port = port
        self.timeout = timeout

    def _call(self, method, params=None):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(self.timeout)
        s.connect((self.host, self.port))
        req = {"id": 1, "method": method}
        if params:
            req["params"] = params
        payload = json.dumps(req).encode()
        s.sendall(struct.pack("!I", len(payload)) + payload)
        raw_len = s.recv(4, socket.MSG_WAITALL)
        resp_len = struct.unpack("!I", raw_len)[0]
        resp = s.recv(resp_len, socket.MSG_WAITALL)
        s.close()
        result = json.loads(resp.decode())
        if not result.get("ok"):
            raise RuntimeError(f"Daemon error: {result}")
        return result["result"]

    def ping(self):
        """心跳检测。"""
        return self._call("ping")

    def screenshot(self, output_path=None, quality=75):
        """全屏截图，返回 dict {width, height, image_b64}。"""
        result = self._call("screenshot_full", {"quality": quality})
        if output_path:
            img = base64.b64decode(result["image_b64"])
            with open(output_path, "wb") as f:
                f.write(img)
            result["saved_to"] = output_path
            result["file_size"] = len(img)
        return result

    def screen_size(self):
        """获取屏幕尺寸。"""
        return self._call("screen_size")

    def scale_factor(self):
        """获取 DPI 缩放。"""
        return self._call("scale_factor")

    def foreground_window(self):
        """获取当前前台窗口信息。"""
        return self._call("foreground_window")

    def click(self, x, y):
        """鼠标左键点击。"""
        return self._call("click", {"x": x, "y": y})

    def double_click(self, x, y):
        """鼠标双击。"""
        return self._call("double_click", {"x": x, "y": y})

    def right_click(self, x, y):
        """鼠标右键。"""
        return self._call("right_click", {"x": x, "y": y})

    def move_mouse(self, x, y):
        """移动鼠标。"""
        return self._call("move_mouse", {"x": x, "y": y})

    def type_text(self, text):
        """键盘输入文本。"""
        return self._call("type_text", {"text": text})

    def key_press(self, keys):
        """按键组合，如 "ctrl+c", "enter"。"""
        return self._call("key_press", {"keys": keys})

    def scroll(self, x, y, amount):
        """滚动滚轮 (正=上, 负=下)。"""
        return self._call("scroll", {"x": x, "y": y, "amount": amount})

    def drag(self, start_x, start_y, end_x, end_y, duration=0.5):
        """拖拽。"""
        return self._call("drag", {
            "start_x": start_x, "start_y": start_y,
            "end_x": end_x, "end_y": end_y, "duration": duration
        })

    def type_cn(self, text):
        """中文/Unicode 输入（通过 Windows Python pyperclip + Ctrl+V）。

        标准 type_text() 使用键盘事件模拟，对中文等非 ASCII 字符
        支持不佳。此方法通过 Windows Python 的 pyperclip 将文本
        复制到系统剪贴板，然后发送 Ctrl+V 粘贴。

        参数:
            text: 要输入的文本（任意 Unicode 字符串）

        用法:
            d.click(500, 700)          # 先点击输入框
            d.type_cn("你好世界")       # 复制 + Ctrl+V 粘贴
            d.screenshot("result.jpg") # 截图验证

        注意:
            - 需要 Windows Python 已安装 pyperclip
            - 首次使用: pip install pyperclip（Windows 端）
            - 可通过环境变量 WINDOWS_PYTHON_PATH 指定 python 路径
        """
        script = f'import pyperclip; pyperclip.copy({repr(text)})'
        cmd = f'"{WINDOWS_PYTHON}" -c "{script}"'
        ret = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if ret.returncode != 0:
            raise RuntimeError(
                f"pyperclip 复制失败: {ret.stderr.strip()}\n"
                f"请确认 Windows Python 已安装 pyperclip:\n"
                f'  cmd.exe /c "{WINDOWS_PYTHON} -m pip install pyperclip"'
            )
        # Ctrl+V 粘贴
        return self.key_press("ctrl+v")


# 使用示例
if __name__ == "__main__":
    d = DaemonClient()
    print("Ping:", d.ping())
    print("Screen:", d.screen_size())
    print("Scale:", d.scale_factor())
    info = d.foreground_window()
    print(f"Window: {info['app_name']} - {info['title']}")
    d.screenshot("/tmp/rpa_desktop.jpg")
    print("Screenshot saved")

    # 中文输入示例
    d.click(500, 700)
    d.type_cn("你好世界")
    d.screenshot("/tmp/cn_input_test.jpg")
    print("中文输入测试截图已保存")
