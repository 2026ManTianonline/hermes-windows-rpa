"""EasyOCR runner — saves results as UTF-8 JSON, no terminal encoding issues"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '新建文件夹', 'Lib', 'site-packages'))

image_path = sys.argv[1] if len(sys.argv) > 1 else r'D:\hermes-windows-rpa\screenshots\contact_list.jpg'
out_path = sys.argv[2] if len(sys.argv) > 2 else r'D:\hermes-windows-rpa\screenshots\ocr_results.json'

import easyocr
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)
results = reader.readtext(image_path)

data = []
for bbox, text, conf in results:
    # y coordinate = top-left corner y
    y = int(bbox[0][1])
    x = int(bbox[0][0])
    data.append({
        'text': text,
        'conf': round(conf * 100),
        'x': x,
        'y': y
    })

# Sort top-to-bottom, then left-to-right
data.sort(key=lambda r: (r['y'], r['x']))

with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'OK: {len(data)} items → {out_path}')
