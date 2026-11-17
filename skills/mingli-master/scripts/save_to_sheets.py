#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
寫入命理紀錄到 Google Sheets(經 Apps Script Web App)
用法: python3 save_to_sheets.py --json '{"姓名":"...","結論":"..."}'
URL 優先序: --url 參數 > config.json(專案根目錄或skill根目錄) > SKILL.md 中「WEBHOOK_URL:」行
首次使用請依 README.md 部署 Apps Script,並將網址填入 config.json(參考 config.example.json)。
純標準庫, 無外部依賴。
"""
import argparse, json, sys, urllib.request, pathlib, re

def find_url():
    skill_root = pathlib.Path(__file__).resolve().parent.parent
    # 1. skill 目錄下的 config.json
    for cfg_path in [skill_root / "config.json", skill_root.parent / "config.json"]:
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                if cfg.get("webhook_url", "").startswith("https://"):
                    return cfg["webhook_url"]
            except Exception:
                pass
    # 2. SKILL.md 裡的 WEBHOOK_URL 行(相容舊版寫法)
    md = skill_root / "SKILL.md"
    if md.exists():
        m = re.search(r"WEBHOOK_URL:\s*(https://\S+)", md.read_text(encoding="utf-8"))
        if m: return m.group(1)
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url"); ap.add_argument("--json", required=True)
    a = ap.parse_args()
    url = a.url or find_url()
    if not url:
        print(json.dumps({"ok": False, "error": "找不到存檔網址。請確認以下任一來源:(1) skill 資料夾內的 config.json(打包前放入,不進 GitHub);(2) 執行時加 --url;(3) SKILL.md 的 WEBHOOK_URL 行"}, ensure_ascii=False)); sys.exit(1)
    data = json.dumps(json.loads(a.json), ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(r.read().decode("utf-8"))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)); sys.exit(1)

if __name__ == "__main__":
    main()
