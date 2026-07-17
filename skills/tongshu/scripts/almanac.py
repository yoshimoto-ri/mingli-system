#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
農民曆擇日工具(lunar-python 引擎, 繁體輸出)
模式1 單日: python3 almanac.py --date 2026-06-20
模式2 擇日: python3 almanac.py --from 2026-06-15 --to 2026-07-15 --event 嫁娶 --shengxiao 馬 [--shengxiao 鼠]
  - 列出區間內「宜」含該用事、且不沖當事人生肖之候選日,附吉時與沖煞
"""
import argparse, json, sys, subprocess
from datetime import datetime, timedelta

def _ensure(pkg, mod):
    try:
        return __import__(mod)
    except ImportError:
        for extra in (["--break-system-packages"], []):
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg] + extra)
                return __import__(mod)
            except Exception:
                continue
        raise

_ensure("lunar-python", "lunar_python")
_ensure("opencc-python-reimplemented", "opencc")
from lunar_python import Solar
from opencc import OpenCC
CC = OpenCC("s2t")
T = lambda x: CC.convert(x)

def day_info(y, m, d, full=True):
    lun = Solar.fromYmd(y, m, d).getLunar()
    leap = "閏" if lun.getMonth() < 0 else ""
    info = {
        "陽曆": f"{y:04d}-{m:02d}-{d:02d}",
        "農曆": f"{T(lun.getYearInGanZhi())}年{leap}{T(lun.getMonthInChinese())}月{T(lun.getDayInChinese())}",
        "干支": f"{lun.getYearInGanZhi()}年 {lun.getMonthInGanZhi()}月 {lun.getDayInGanZhi()}日",
        "沖": T(lun.getDayChongDesc()), "煞方": "煞" + T(lun.getDaySha()),
        "宜": [T(x) for x in lun.getDayYi()],
        "忌": [T(x) for x in lun.getDayJi()],
        "吉時": [], "凶時": [],
    }
    for t in lun.getTimes():
        s = f"{t.getGanZhi()}時({t.getMinHm()}-{t.getMaxHm()}) 沖{T(t.getChongDesc())}"
        (info["吉時"] if t.getTianShenLuck() == "吉" else info["凶時"]).append(s)
    if full:
        info.update({
            "十二建除": T(lun.getZhiXing()) + "日",
            "值日天神": f"{T(lun.getDayTianShen())}({lun.getDayTianShenLuck()})",
            "二十八宿": f"{T(lun.getXiu())}宿({lun.getXiuLuck()})",
            "彭祖百忌": T(lun.getPengZuGan() + ";" + lun.getPengZuZhi()),
            "吉神方位": {"喜神": T(lun.getDayPositionXiDesc()), "財神": T(lun.getDayPositionCaiDesc()),
                        "福神": T(lun.getDayPositionFuDesc()), "陽貴神": T(lun.getDayPositionYangGuiDesc())},
            "節氣": T(lun.getPrevJieQi(True).getName()) + "後",
        })
    return info

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--from", dest="d_from")
    ap.add_argument("--to", dest="d_to")
    ap.add_argument("--event", help="用事關鍵字, 如 嫁娶/開市/入宅/動土/安床/出行/簽約(交易)/安葬")
    ap.add_argument("--shengxiao", action="append", default=[], help="當事人生肖(可多個), 沖此生肖之日剔除")
    a = ap.parse_args()

    if a.date:
        y, m, d = map(int, a.date.split("-"))
        print(json.dumps(day_info(y, m, d), ensure_ascii=False, indent=1)); return

    if not (a.d_from and a.d_to and a.event):
        print(json.dumps({"error": "擇日模式需 --from --to --event"}, ensure_ascii=False)); sys.exit(1)
    cur = datetime.strptime(a.d_from, "%Y-%m-%d")
    end = datetime.strptime(a.d_to, "%Y-%m-%d")
    cands, skipped = [], 0
    while cur <= end:
        info = day_info(cur.year, cur.month, cur.day, full=False)
        ok = any(a.event in yi for yi in info["宜"]) and "諸事不宜" not in info["宜"]
        clash = any(sx in info["沖"] for sx in a.shengxiao)
        if ok and not clash:
            lun = Solar.fromYmd(cur.year, cur.month, cur.day).getLunar()
            info["十二建除"] = T(lun.getZhiXing()) + "日"
            info["週幾"] = ["一","二","三","四","五","六","日"][cur.weekday()]
            del info["忌"], info["凶時"]
            cands.append(info)
        elif ok:
            skipped += 1
        cur += timedelta(days=1)
    print(json.dumps({"用事": a.event, "區間": f"{a.d_from}~{a.d_to}",
                      "避沖生肖": a.shengxiao, "因沖生肖剔除日數": skipped,
                      "候選日": cands}, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
