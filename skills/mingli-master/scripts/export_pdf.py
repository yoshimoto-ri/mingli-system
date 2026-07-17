#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命理報告 → PDF + 上傳 Google Drive「命理系統」資料夾
用法: python3 export_pdf.py --name "王小明" --date "2026-06-13" --content "報告全文..."
     可選: --drive-token "OAuth token" 上傳到 Google Drive
輸出: PDF 檔案路徑
"""
import argparse, json, os, sys, subprocess, tempfile
from datetime import datetime

def _ensure(pkg, mod):
    try: return __import__(mod)
    except ImportError:
        for extra in (["--break-system-packages"],[]):
            try: subprocess.check_call([sys.executable,"-m","pip","install","-q",pkg]+extra); return __import__(mod)
            except: continue
        raise

reportlab = _ensure("reportlab","reportlab")
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_PATHS = [
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]

def reg_font():
    for p in FONT_PATHS:
        if os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont("ZH", p))
                return "ZH"
            except: continue
    return "Helvetica"

def make_pdf(name, date, content, out_path):
    font = reg_font()
    doc = SimpleDocTemplate(out_path, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", fontName=font, fontSize=16, spaceAfter=8, leading=22)
    h2 = ParagraphStyle("h2", fontName=font, fontSize=13, spaceAfter=6, leading=18, textColor="#333333")
    body = ParagraphStyle("body", fontName=font, fontSize=11, spaceAfter=4, leading=18)
    small = ParagraphStyle("small", fontName=font, fontSize=9, textColor="#888888")

    story = [
        Paragraph(f"命理分析報告", h1),
        Paragraph(f"當事人：{name}　　日期：{date}", small),
        Spacer(1, 6*mm),
    ]
    for line in content.split("\n"):
        line = line.strip()
        if not line: story.append(Spacer(1, 3*mm)); continue
        if line.startswith("## "): story.append(Paragraph(line[3:], h2))
        elif line.startswith("# "): story.append(Paragraph(line[2:], h1))
        else: story.append(Paragraph(line.replace("**",""), body))

    doc.build(story)
    return out_path

def upload_drive(pdf_path, filename, webhook_url):
    """透過 Apps Script 端點上傳(base64 POST)"""
    import urllib.request, base64
    data = open(pdf_path,"rb").read()
    payload = json.dumps({"action":"upload_pdf","filename":filename,
                          "data":base64.b64encode(data).decode()}).encode()
    req = urllib.request.Request(webhook_url, data=payload,
          headers={"Content-Type":"application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"ok":False,"error":str(e)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--content", required=True)
    ap.add_argument("--webhook", help="Apps Script URL(含upload_pdf處理)")
    ap.add_argument("--out-dir", default="/tmp")
    a = ap.parse_args()

    filename = f"{a.name}_{a.date}.pdf"
    out_path = os.path.join(a.out_dir, filename)
    make_pdf(a.name, a.date, a.content, out_path)
    result = {"ok":True, "pdf_path":out_path, "filename":filename}
    if a.webhook:
        r = upload_drive(out_path, filename, a.webhook)
        result["drive"] = r
    print(json.dumps(result, ensure_ascii=False))

if __name__=="__main__":
    main()
