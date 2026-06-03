#!/usr/bin/env python3
"""Hermes RPA — OCR + 视觉辅助文字提取（一条命令完成）

在 Hermes 会话中用法:

  1. 截全屏定位区域:
     >>> mcp_desktop_screenshot()

  2. 用视觉模型找出聊天区域坐标（不读字，只找位置）
     >>> vision_analyze("请找出QQ聊天气泡区域的坐标范围")

  3. 裁剪该区域并 OCR（精确提取文字）:
     >>> terminal(command='python3 D:/hermes-windows-rpa/scripts/rpa_ocr_flow.py --region x y w h')
     
  4. 基于 OCR 结果做理解（LM 读文字，不是看图片，不会再幻视）

快捷方式 — 截全屏并 OCR:
  >>> terminal(command='python3 D:/hermes-windows-rpa/scripts/rpa_ocr_flow.py --screenshot')
  
对已有截图做区域 OCR:
  >>> terminal(command='python3 D:/hermes-windows-rpa/scripts/rpa_ocr_flow.py 图片路径 --region x y w h')
"""

import sys
import json
import subprocess
from pathlib import Path
import tempfile

try:
    import cv2
    import numpy as np
except ImportError:
    print("❌ 需要 OpenCV: pip install opencv-python")
    sys.exit(1)


# ============================================================
# OCR 引擎
# ============================================================

def ocr_preprocess(image_array, scale=3):
    """预处理图像以提升 Tesseract 识别率。"""
    scaled = cv2.resize(image_array, None, fx=scale, fy=scale,
                        interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    binary = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, blockSize=31, C=5
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    return cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)


def run_ocr_text(image_array):
    """对预处理后的图像运行 Tesseract，返回纯文本。"""
    temp_path = "/tmp/_ocr_temp.png"
    cv2.imwrite(temp_path, image_array)
    cmd = [
        "tesseract", temp_path, "stdout",
        "-l", "chi_sim+eng",
        "--psm", "6", "--oem", "1",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def ocr_image(img, scale=3):
    """完整 OCR 流程。"""
    processed = ocr_preprocess(img, scale=scale)
    return run_ocr_text(processed)


# ============================================================
# 截图工具
# ============================================================

def take_screenshot(output_path):
    """通过 MCP 桌面工具截图（通过 WSL terminal 间接调用）。"""
    # 直接调用 MCP 截图工具
    import subprocess
    # 注意：这个脚本通常由 Hermes 通过 terminal() 调用，
    # 而 MCP 截图必须由 Hermes 自身调用
    # 所以这里只是占位，实际使用时在 Hermes 中先截图
    print("❌ 请先在 Hermes 会话中执行: mcp_desktop_screenshot()")
    print("   然后将截图路径传给此脚本")
    return None


# ============================================================
# 主流程
# ============================================================

def full_ocr_workflow(image_path, region=None):
    """完整工作流：加载 → 裁剪（可选）→ OCR → 输出。"""
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"❌ 无法读取: {image_path}")
        return None

    h, w = img.shape[:2]

    if region:
        x, y, rw, rh = region
        img = img[y:y+rh, x:x+rw]
        print(f"📐 裁剪区域: ({x},{y}) {rw}x{rh}  ← 原图 {w}x{h}", file=sys.stderr)

    text = ocr_image(img)
    return text


def main():
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        return

    # 解析参数
    image_path = None
    region = None
    save_to = None

    i = 0
    while i < len(args):
        if args[i] == "--region" and i + 4 < len(args):
            region = (int(args[i+1]), int(args[i+2]),
                      int(args[i+3]), int(args[i+4]))
            i += 4
        elif args[i] == "--save" and i + 1 < len(args):
            save_to = args[i+1]
            i += 1
        elif args[i].startswith("--"):
            pass  # skip other flags
        else:
            image_path = args[i]
        i += 1

    if not image_path:
        print("❌ 请提供图片路径")
        sys.exit(1)

    if not Path(image_path).exists():
        print(f"❌ 文件不存在: {image_path}")
        sys.exit(1)

    text = full_ocr_workflow(image_path, region)

    if text:
        print("=" * 50)
        print("📝 OCR 提取结果:")
        print("=" * 50)
        print(text)
        print("=" * 50)

        if save_to:
            with open(save_to, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"💾 已保存到: {save_to}")
    else:
        print("❌ OCR 未能提取到文字。")


if __name__ == "__main__":
    main()
