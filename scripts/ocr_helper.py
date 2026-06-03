#!/usr/bin/env python3
"""Hermes RPA — OCR 文字提取工具 v3

基于 Tesseract + OpenCV 预处理，提供高精度中文 OCR。
消除视觉模型对文字的幻视问题。

用法:
  python3 ocr_helper.py <图片路径>                         # 完整 OCR（Otsu 阈值）
  python3 ocr_helper.py <图片路径> --crop x y w h          # 只 OCR 指定区域
  python3 ocr_helper.py <图片路径> --adaptive               # 自适应阈值（备选）
  python3 ocr_helper.py <图片路径> --crop x y w h --json   # 区域 OCR + JSON

示例:
  python3 ocr_helper.py screenshot.jpg                    # 推荐
  python3 ocr_helper.py screenshot.jpg --crop 100 200 400 300 --json

推荐工作流:
  1. mcp_desktop_screenshot()                       # 截全屏
  2. mcp_desktop_screenshot_region(212,12,250,790)  # 截聊天区域（QQ右侧）
  3. python3 ocr_helper.py 区域截图.jpg               # OCR 提取文字（不幻视）
  4. LLM 基于 OCR 结果做理解                          # 精准！
"""

import sys
import json
import subprocess
from pathlib import Path

try:
    import cv2
    import numpy as np
except ImportError:
    print("❌ 需要安装 OpenCV: pip install opencv-python")
    sys.exit(1)


def preprocess_image(image_array, scale=3, method="otsu"):
    """图像预处理：放大 + 灰度 + 降噪 + 二值化。

    method:
      "otsu" — Otsu 全局阈值（推荐，对聊天截图效果好）
      "adaptive" — 自适应阈值（适合光照不均的图片）
    """
    scaled = cv2.resize(image_array, None, fx=scale, fy=scale,
                        interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    if method == "adaptive":
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, blockSize=31, C=5
        )
    else:
        # Otsu 全局阈值 — 对聊天截图效果更好
        _, binary = cv2.threshold(
            denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    return cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)


def run_tesseract_txt(image_array, lang="chi_sim+eng", psm=6):
    """纯文本输出。"""
    temp_path = "/tmp/_ocr_temp.png"
    cv2.imwrite(temp_path, image_array)
    cmd = [
        "tesseract", temp_path, "stdout",
        "-l", lang, "--psm", str(psm), "--oem", "1",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return None, result.stderr
    return result.stdout.strip(), None


def run_tesseract_tsv(image_array, lang="chi_sim+eng", psm=6):
    """含坐标和置信度的详细信息。"""
    temp_path = "/tmp/_ocr_temp.png"
    cv2.imwrite(temp_path, image_array)
    cmd = [
        "tesseract", temp_path, "stdout",
        "-l", lang, "--psm", str(psm), "--oem", "1", "tsv"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return []

    lines = []
    tsv_data = result.stdout.strip().split("\n")
    if len(tsv_data) > 1:
        headers = tsv_data[0].split("\t")
        for row in tsv_data[1:]:
            cols = row.split("\t")
            if len(cols) >= len(headers):
                row_data = dict(zip(headers, cols))
                text = row_data.get("text", "").strip()
                conf = row_data.get("conf", "-1")
                if text and conf != "-1":
                    try:
                        conf_val = int(conf) / 100.0
                        if conf_val > 0.3:
                            lines.append({
                                "text": text,
                                "confidence": round(conf_val, 3),
                            })
                    except ValueError:
                        pass
    return lines


def load_image(path):
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(f"❌ 无法读取图片: {path}")
    return img


def do_ocr(image_array, output_format="text", method="otsu"):
    """对图像数组执行 OCR。"""
    processed = preprocess_image(image_array, method=method)
    if output_format == "json":
        lines = run_tesseract_tsv(processed)
        text, _ = run_tesseract_txt(processed)
        return {
            "text": text or "",
            "lines": lines,
            "line_count": len(lines),
        }
    else:
        text, error = run_tesseract_txt(processed)
        if text:
            return text
        return f"[OCR 错误] {error}"


def main():
    if len(sys.argv) < 2 or "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        sys.exit(1)

    image_path = sys.argv[1]
    if not Path(image_path).exists():
        print(f"❌ 文件不存在: {image_path}")
        sys.exit(1)

    # 解析参数
    output_format = "text"
    crop = None
    method = "otsu"

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--json":
            output_format = "json"
        elif args[i] == "--adaptive":
            method = "adaptive"
        elif args[i] == "--crop" and i + 4 < len(args):
            crop = (int(args[i+1]), int(args[i+2]),
                    int(args[i+3]), int(args[i+4]))
            i += 4
        i += 1

    # 加载图片
    img = load_image(image_path)
    h, w = img.shape[:2]

    if crop:
        x, y, cw, ch = crop
        img = img[y:y+ch, x:x+cw]
        print(f"📐 裁剪: ({x},{y}) {cw}x{ch}", file=sys.stderr)

    # OCR
    result = do_ocr(img, output_format, method=method)

    if output_format == "json":
        output = {
            "file": image_path,
            "image_size": {"w": w, "h": h},
            "method": method,
            "ocr_region": {"x": crop[0], "y": crop[1],
                           "w": crop[2], "h": crop[3]} if crop else None,
        }
        output.update(result)
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(result)


if __name__ == "__main__":
    main()
