#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
曆法回歸驗證:春節、立春、春分 三方比對
  1. 立春/春分時刻:Swiss Ephemeris(boundaries.py) vs lunar-python 節氣表(誤差上限 --tol-sec 秒)
  2. 春節日期:lunar-python vs 獨立天文規則(冬至在十一月、無中氣置閏、UTC+8 定日)
  3. (選用 --hko)三項日期 vs 香港天文台《公曆與農曆日期對照表》

用法:
  python3 verify_calendar.py                      # 預設 1937~今年,不連網
  python3 verify_calendar.py --start 1901 --end 2100 --hko --csv result.csv
結束碼:全部一致 0;有任何不符 1
"""
import argparse, csv, os, re, sys, urllib.request
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import swisseph as swe
from lunar_python import Lunar
from boundaries import sun_cross, new_moon

UTC8 = ZoneInfo("Etc/GMT-8")
HKO_URL = "https://www.hko.gov.hk/tc/gts/time/calendar/text/files/T{y}c.txt"

def to8(jd):
    y, m, d, h = swe.revjul(jd)
    return (datetime(y, m, d, tzinfo=ZoneInfo("UTC")) + timedelta(hours=h)).astimezone(UTC8).replace(tzinfo=None)

def lp_term(y, name):
    s = Lunar.fromYmd(y, 1, 1).getJieQiTable()[name]
    return datetime(s.getYear(), s.getMonth(), s.getDay(), s.getHour(), s.getMinute(), s.getSecond())

def lp_cny(y):
    s = Lunar.fromYmd(y, 1, 1).getSolar()
    return date(s.getYear(), s.getMonth(), s.getDay())

def astro_cny(y):
    """獨立天文規則推正月初一。"""
    day = lambda jd: to8(jd).date()
    ws = lambda yy: sun_cross(270, swe.julday(yy, 12, 10), +1)
    w0, w1 = ws(y - 1), ws(y)
    m = new_moon(w0 + 1, -1)
    if day(m) > day(w0):
        m = new_moon(m - 1, -1)
    moons = [m]
    while day(moons[-1]) <= day(w1):
        moons.append(new_moon(moons[-1] + 2, +1))
    months = moons[:-1]                     # 十一月起,到含次一冬至之月
    leap = None
    if len(months) - 1 == 13:               # 兩冬至間 13 個月 → 置閏
        for i in range(1, len(months)):
            a, b = day(months[i]), day(moons[i + 1])
            has_zq = any(a <= day(sun_cross(L, months[i] - 1, +1)) < b for L in range(0, 360, 30))
            if not has_zq:
                leap = i; break
    idx = 3 if (leap is not None and leap <= 2) else 2   # 十一月=0、十二月=1、正月=2
    return day(months[idx])

def hko_dates(y, cache_dir):
    os.makedirs(cache_dir, exist_ok=True)
    p = os.path.join(cache_dir, f"T{y}c.txt")
    if not os.path.exists(p) or os.path.getsize(p) == 0:
        req = urllib.request.Request(HKO_URL.format(y=y), headers={"User-Agent": "mingli-system calendar check"})
        with urllib.request.urlopen(req, timeout=30) as r, open(p, "wb") as f:
            f.write(r.read())
    out = {}
    for line in open(p, encoding="utf-8-sig"):
        m = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日\s+(\S+)\s+\S+\s*(\S*)", line)
        if not m: continue
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if m.group(4) == "正月": out.setdefault("春節", d)
        if m.group(5) in ("立春", "春分"): out.setdefault(m.group(5), d)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=1937)
    ap.add_argument("--end", type=int, default=datetime.now().year)
    ap.add_argument("--hko", action="store_true", help="下載香港天文台對照表比對(需連網)")
    ap.add_argument("--tol-sec", type=float, default=60, help="節氣時刻容許誤差(秒),預設 60")
    ap.add_argument("--csv", help="輸出逐年明細 CSV")
    ap.add_argument("--cache", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".hko_cache"))
    a = ap.parse_args()

    rows, fails, max_sec = [], [], 0.0
    for y in range(a.start, a.end + 1):
        lc = to8(sun_cross(315, swe.julday(y, 1, 20), +1))
        cf = to8(sun_cross(0, swe.julday(y, 3, 10), +1))
        d_lc = abs((lc - lp_term(y, "立春")).total_seconds())
        d_cf = abs((cf - lp_term(y, "春分")).total_seconds())
        max_sec = max(max_sec, d_lc, d_cf)
        cny, cny2 = lp_cny(y), astro_cny(y)
        r = {"年": y, "春節": cny.isoformat(), "立春(UTC+8)": lc.strftime("%Y-%m-%d %H:%M"),
             "春分(UTC+8)": cf.strftime("%Y-%m-%d %H:%M"), "春節-立春(天)": (cny - lc.date()).days,
             "節氣時刻誤差(秒)": round(max(d_lc, d_cf), 1),
             "春節天文核對": "一致" if cny == cny2 else f"不符({cny2})"}
        if d_lc > a.tol_sec or d_cf > a.tol_sec: fails.append(f"{y} 節氣時刻誤差 {max(d_lc, d_cf):.1f} 秒")
        if cny != cny2: fails.append(f"{y} 春節 lunar-python={cny} 天文規則={cny2}")
        if a.hko:
            try:
                h = hko_dates(y, a.cache)
                ok = (h.get("春節"), h.get("立春"), h.get("春分")) == (cny, lc.date(), cf.date())
                r["香港天文台核對"] = "一致" if ok else f"不符({h})"
                if not ok: fails.append(f"{y} 香港天文台 {h} vs 系統 春節{cny} 立春{lc.date()} 春分{cf.date()}")
            except Exception as e:
                r["香港天文台核對"] = f"下載失敗:{e}"
                fails.append(f"{y} 香港天文台下載失敗:{e}")
        rows.append(r)

    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
    n = len(rows)
    print(f"驗證年份 {a.start}~{a.end},共 {n} 年")
    print(f"節氣時刻(立春/春分)兩套算法最大誤差:{max_sec:.1f} 秒")
    print(f"春節日期兩套算法:{'全部一致' if not any('春節 lunar' in x for x in fails) else '有不符'}")
    if a.hko: print(f"香港天文台比對:{'全部一致' if not any('香港' in x for x in fails) else '有不符'}")
    later = sum(1 for r in rows if r["春節-立春(天)"] > 0)
    earlier = sum(1 for r in rows if r["春節-立春(天)"] < 0)
    print(f"春節晚於立春 {later} 年、早於立春 {earlier} 年、同日 {n - later - earlier} 年")
    if fails:
        print("\n不符項目:"); [print(" -", x) for x in fails]
        sys.exit(1)
    print("\n結果:全部通過 ✓")

if __name__ == "__main__":
    main()
