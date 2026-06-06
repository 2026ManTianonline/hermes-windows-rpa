#!/usr/bin/env python3
"""
EasyOCR WSL wrapper — call from WSL, get clean UTF-8 output.

Usage:
  python3 easyocr_reader.py <screenshot_path>

Example:
  python3 easyocr_reader.py /home/h/.hermes/image_cache/img_xxx.jpg
  python3 easyocr_reader.py /mnt/d/screenshots/test.png

Output: JSON array of {text, conf, x, y} sorted top→bottom, left→right.
"""

import sys, os, json, subprocess, tempfile

# ── Config ──────────────────────────────────────────────────
WINDOWS_PYTHON = r"/mnt/d/新建文件夹/python.exe"
EASYOCR_RUNNER = r"D:\hermes-windows-rpa\scripts\easyocr_runner.py"  # passed to Windows Python
WORK_DIR = r"D:\hermes-windows-rpa\screenshots"
# ────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 easyocr_reader.py <screenshot_path>", file=sys.stderr)
        sys.exit(1)

    src = sys.argv[1]

    # Resolve WSL path → Windows path
    if src.startswith("/mnt/"):
        parts = src.split("/")
        drive_letter = parts[2].upper()
        win_path = drive_letter + ":" + "\\".join(parts[3:])
    elif src.startswith("/home/"):
        # Copy to Windows temp dir
        os.makedirs("/mnt/d/hermes-windows-rpa/screenshots", exist_ok=True)
        basename = os.path.basename(src)
        dst = f"/mnt/d/hermes-windows-rpa/screenshots/{basename}"
        subprocess.run(["cp", src, dst], check=True)
        win_path = f"D:\\hermes-windows-rpa\\screenshots\\{basename}"
    else:
        print(f"Unsupported path: {src}", file=sys.stderr)
        sys.exit(1)

    # Temp output file
    out_name = f"ocr_{os.urandom(4).hex()}.json"
    out_win = f"{WORK_DIR}\\{out_name}"
    out_wsl = f"/mnt/d/hermes-windows-rpa/screenshots/{out_name}"

    # Run EasyOCR on Windows — stdout may have non-UTF-8 bytes, ignore it
    cmd = [WINDOWS_PYTHON, EASYOCR_RUNNER, win_path, out_win]
    result = subprocess.run(cmd, capture_output=True, timeout=300)

    if result.returncode != 0:
        err = result.stderr.decode("utf-8", errors="replace")
        print(f"EasyOCR failed: {err}", file=sys.stderr)
        sys.exit(1)

    # Read results
    with open(out_wsl, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Output clean JSON to stdout
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    print()  # trailing newline

    # Cleanup temp file
    os.remove(out_wsl)


if __name__ == "__main__":
    main()
