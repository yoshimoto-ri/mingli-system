#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
年度行運精確事件表(應期用)——取代「每月取樣」的粗估
python3 transits.py --date "1963-08-15 22:30" --tz Asia/Taipei --lat 25.04 --lon 121.56 --year 2027
  選項: --house P|W  (行運入宮所用本命宮制;小限一律整宮制)
輸出 JSON:
  1. 逆行表:水金火木土天海冥 停滯轉逆/轉順精確時刻 + 水金火 前後陰影期
  2. 換座/換宮:行星進入新星座、進入本命新宮位的日期
  3. 精準相位:行運 火木土天海冥 對本命 日月水金火木土/ASC/MC 合六刑拱沖 的精準日(含逆行多次通過)
  4. 日月食:日期、星座度數、落本命宮位、與本命點 3 度內合沖
  5. 年度小限(Annual Profection):小限宮、年主星(古典七政)
所有時刻以 --tz 當地時間表示;星曆 Swiss Ephemeris (Moshier)。
"""
import argparse, json, sys, subprocess
from datetime import datetime

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

swe = _ensure("pyswisseph", "swisseph")
from zoneinfo import ZoneInfo

FL = swe.FLG_MOSEPH | swe.FLG_SPEED
SIGNS = ["牡羊","金牛","雙子","巨蟹","獅子","處女","天秤","天蠍","射手","摩羯","水瓶","雙魚"]
TRAD_RULER = ["火星","金星","水星","月亮","太陽","水星","金星","火星","木星","土星","土星","木星"]
P = {"太陽": swe.SUN, "月亮": swe.MOON, "水星": swe.MERCURY, "金星": swe.VENUS, "火星": swe.MARS,
     "木星": swe.JUPITER, "土星": swe.SATURN, "天王星": swe.URANUS, "海王星": swe.NEPTUNE, "冥王星": swe.PLUTO}
RETRO_PL = ["水星","金星","火星","木星","土星","天王星","海王星","冥王星"]
SHADOW_PL = ["水星","金星","火星"]
INGRESS_PL = ["水星","金星","火星","木星","土星","天王星","海王星","冥王星"]
ASPECT_PL = ["火星","木星","土星","天王星","海王星","冥王星"]
NATAL_PTS = ["太陽","月亮","水星","金星","火星","木星","土星"]
ASPECTS = [(0,"合"),(60,"六合"),(90,"刑"),(120,"拱"),(180,"沖")]

def lon_spd(jd, name):
    p, _ = swe.calc_ut(jd, P[name], FL)
    return p[0] % 360, p[3]

def fmt(lon):
    d = lon % 30
    return f"{SIGNS[int(lon//30)]}{int(d)}°{int(d%1*60):02d}'"

class T:
    def __init__(self, tz): self.tz = ZoneInfo(tz)
    def jd(self, dt_local):
        u = dt_local.replace(tzinfo=self.tz).astimezone(ZoneInfo("UTC"))
        return swe.julday(u.year, u.month, u.day, u.hour + u.minute/60 + u.second/3600)
    def s(self, jd):
        y, m, d, h = swe.revjul(jd)
        hh = int(h); mm = int(round((h-hh)*60))
        if mm == 60: hh, mm = hh+1, 0
        u = datetime(y, m, d, 0, 0, tzinfo=ZoneInfo("UTC"))
        from datetime import timedelta
        u = u + timedelta(hours=hh, minutes=mm)
        return u.astimezone(self.tz).strftime("%Y-%m-%d %H:%M")

def bisect(f, a, b, tol=1/1440):
    fa = f(a)
    for _ in range(60):
        m = (a+b)/2; fm = f(m)
        if (fm > 0) == (fa > 0): a, fa = m, fm
        else: b = m
        if b - a < tol: break
    return (a+b)/2

def house_of(lon, cusps):
    for i in range(12):
        a, b = cusps[i], cusps[(i+1) % 12]
        if (a <= lon < b) if a < b else (lon >= a or lon < b):
            return i + 1
    return 12

def sdiff(a, b):
    return ((a - b + 180) % 360) - 180

# ---------- 逆行 ----------
def stations(name, j0, j1):
    out, step = [], 1.0
    j = j0; _, sp = lon_spd(j, name)
    while j < j1:
        jn = j + step; _, spn = lon_spd(jn, name)
        if (sp < 0) != (spn < 0):
            js = bisect(lambda x: lon_spd(x, name)[1], j, jn)
            out.append(("R" if spn < 0 else "D", js, lon_spd(js, name)[0]))
        j, sp = jn, spn
    return out

def cross_time(name, target_lon, ja, jb, step=0.5):
    """在 [ja,jb] 內找行星經度通過 target_lon 的第一個時刻"""
    j = ja; d0 = sdiff(lon_spd(j, name)[0], target_lon)
    while j < jb:
        jn = min(j + step, jb); d1 = sdiff(lon_spd(jn, name)[0], target_lon)
        if (d0 > 0) != (d1 > 0) and abs(d0) < 20 and abs(d1) < 20:
            return bisect(lambda x: sdiff(lon_spd(x, name)[0], target_lon), j, jn)
        j, d0 = jn, d1
    return None

def retro_table(t, j0, j1, cusps):
    res = {}
    for n in RETRO_PL:
        st = stations(n, j0 - 400, j1 + 400)
        periods = []
        for k in range(len(st)-1):
            if st[k][0] == "R" and st[k+1][0] == "D":
                r, d = st[k], st[k+1]
                if d[1] < j0 or r[1] > j1: continue
                item = {"轉逆": t.s(r[1]), "逆行起點": fmt(r[2]), "轉順": t.s(d[1]), "逆行終點": fmt(d[2]),
                        "本命宮位": sorted({house_of(r[2], cusps), house_of(d[2], cusps)})}
                if n in SHADOW_PL:
                    pre = cross_time(n, d[2], r[1] - 80, r[1])
                    post = cross_time(n, r[2], d[1], d[1] + 80)
                    item["前陰影起"] = t.s(pre) if pre else None
                    item["後陰影止"] = t.s(post) if post else None
                periods.append(item)
        res[n] = periods or "本年無逆行"
    return res

# ---------- 換座 / 換宮 ----------
def ingresses(t, j0, j1, cusps):
    out = []
    for n in INGRESS_PL:
        j = j0; l0, _ = lon_spd(j, n)
        step = 0.25 if n in ("水星", "金星", "火星") else 1.0
        while j < j1:
            jn = j + step; l1, sp = lon_spd(jn, n)
            if int(l0 // 30) != int(l1 // 30):
                bd = (int(l1//30) * 30) if sp >= 0 else (int(l0//30) * 30)
                jx = bisect(lambda x: sdiff(lon_spd(x, n)[0], bd), j, jn)
                out.append({"時間": t.s(jx), "行星": n, "事件": f"進入{SIGNS[int(l1//30)]}" + ("(逆行退回)" if sp < 0 else "")})
            h0, h1 = house_of(l0, cusps), house_of(l1, cusps)
            if h0 != h1 and n not in ("水星", "金星"):
                cb = cusps[(h1-1) if sp >= 0 else (h0-1)]
                jx = bisect(lambda x: sdiff(lon_spd(x, n)[0], cb), j, jn)
                out.append({"時間": t.s(jx), "行星": n, "事件": f"進入本命第{h1}宮" + ("(逆行退回)" if sp < 0 else "")})
            j, l0 = jn, l1
    return sorted(out, key=lambda x: x["時間"])

# ---------- 精準相位 ----------
def exact_aspects(t, j0, j1, natal):
    out = []
    for n in ASPECT_PL:
        for pt, nl in natal.items():
            for ang, an in ASPECTS:
                for sign in ((1,) if ang in (0, 180) else (1, -1)):
                    tgt = (nl + sign*ang) % 360
                    f = lambda x: sdiff(lon_spd(x, n)[0], tgt)
                    j = j0; d0 = f(j)
                    while j < j1:
                        jn = j + 1.0; d1 = f(jn)
                        if (d0 > 0) != (d1 > 0) and abs(d0) < 5 and abs(d1) < 5:
                            jx = bisect(f, j, jn)
                            _, sp = lon_spd(jx, n)
                            out.append({"時間": t.s(jx), "相位": f"行運{n}{an}本命{pt}",
                                        "度數": fmt(tgt), "行運狀態": "逆行中" if sp < 0 else "順行"})
                        j, d0 = jn, d1
    return sorted(out, key=lambda x: x["時間"])

# ---------- 日月食 ----------
def eclipses(t, j0, j1, cusps, natal):
    out = []
    kinds = [(swe.ECL_TOTAL, "全"), (swe.ECL_ANNULAR, "環"), (swe.ECL_PARTIAL, "偏"), (swe.ECL_PENUMBRAL, "半影")]
    for fn, nm, body in ((swe.sol_eclipse_when_glob, "日食", "太陽"), (swe.lun_eclipse_when, "月食", "月亮")):
        j = j0
        while True:
            typ, tm = fn(j, swe.FLG_MOSEPH)
            jm = tm[0]
            if jm > j1: break
            l, _ = lon_spd(jm, body)
            k = next((v for f, v in kinds if typ & f), "")
            hits = []
            for pt, nl in natal.items():
                for ang, an in ((0, "合"), (180, "沖")):
                    if abs(sdiff(l, (nl + ang) % 360)) <= 3:
                        hits.append(f"{an}本命{pt}")
            out.append({"時間": t.s(jm), "類型": k + nm, "位置": fmt(l), "本命宮位": house_of(l, cusps),
                        "觸及本命點(3°內)": hits or "無"})
            j = jm + 20
    return sorted(out, key=lambda x: x["時間"])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True); ap.add_argument("--tz", required=True)
    ap.add_argument("--lat", type=float, required=True); ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--house", default="P", choices=["P", "W"])
    a = ap.parse_args()
    t = T(a.tz)
    bdt = datetime.strptime(a.date, "%Y-%m-%d %H:%M")
    jb = t.jd(bdt)
    cusps_p, ascmc = swe.houses(jb, a.lat, a.lon, b'P')
    asc_sign = int(ascmc[0] // 30)
    cusps = list(cusps_p) if a.house == "P" else [((asc_sign + i) * 30) % 360 for i in range(12)]
    natal = {n: lon_spd(jb, n)[0] for n in NATAL_PTS}
    natal["上升"] = ascmc[0] % 360; natal["天頂"] = ascmc[1] % 360
    j0 = t.jd(datetime(a.year, 1, 1)); j1 = t.jd(datetime(a.year + 1, 1, 1))

    # 小限:生日當天換限,年齡 0 歲 = 第1宮(整宮制)
    prof = []
    for age in (a.year - bdt.year - 1, a.year - bdt.year):
        sg = (asc_sign + age) % 12
        start = f"{bdt.year+age}-{bdt.month:02d}-{bdt.day:02d}"
        end = f"{bdt.year+age+1}-{bdt.month:02d}-{bdt.day:02d}"
        prof.append({"期間": f"{start} ~ {end}", "足歲": age, "小限宮": f"第{age%12+1}宮({SIGNS[sg]})",
                     "年主星": TRAD_RULER[sg]})
    sun_h = house_of(natal["太陽"], list(cusps_p))
    out = {"本命": {"上升": fmt(natal["上升"]), "天頂": fmt(natal["天頂"]),
                   "日夜盤": "日盤" if 7 <= sun_h <= 12 else "夜盤",
                   "行運入宮宮制": "Placidus" if a.house == "P" else "整宮制"},
           "年度小限": prof,
           "逆行表": retro_table(t, j0, j1, cusps),
           "日月食": eclipses(t, j0, j1, cusps, natal),
           "精準相位": exact_aspects(t, j0, j1, natal),
           "換座換宮": ingresses(t, j0, j1, cusps),
           "說明": "逆行/陰影期為流月判斷重點;精準相位前後約1-2週(外行星可達數週)為作用期,逆行造成的多次通過視為同一事件的反覆。"}
    print(json.dumps(out, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
