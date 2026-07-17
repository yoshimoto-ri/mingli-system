#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
西洋占星排盤(Swiss Ephemeris / Moshier, 免星曆檔)
本命盤: python3 natal.py --date "1990-08-15 23:15" --tz Asia/Taipei --lat 25.04 --lon 121.56
  選項: --house W (整宮制,古典用) 預設 P (Placidus)
擇日模式: python3 natal.py --electional "2026-06-20 10:00" --tz Asia/Taipei --lat 25.04 --lon 121.56
輸出 JSON(行星星座/宮位/逆行/廟旺陷落、相位、四軸、月相、月空亡VOC)
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

swe = _ensure("pyswisseph", "swisseph")
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

SIGNS = ["牡羊","金牛","雙子","巨蟹","獅子","處女","天秤","天蠍","射手","摩羯","水瓶","雙魚"]
PLANETS = [("太陽",swe.SUN),("月亮",swe.MOON),("水星",swe.MERCURY),("金星",swe.VENUS),("火星",swe.MARS),
           ("木星",swe.JUPITER),("土星",swe.SATURN),("天王星",swe.URANUS),("海王星",swe.NEPTUNE),
           ("冥王星",swe.PLUTO),("北交點",swe.TRUE_NODE)]
DOMICILE = {"太陽":[4],"月亮":[3],"水星":[2,5],"金星":[1,6],"火星":[0,7],"木星":[8,11],"土星":[9,10],
            "天王星":[10],"海王星":[11],"冥王星":[7]}
EXALT = {"太陽":0,"月亮":1,"水星":5,"金星":11,"火星":9,"木星":3,"土星":6}
ASPECTS = [(0,"合相",8),(60,"六分相",5),(90,"四分相",7),(120,"三分相",7),(180,"對分相",8)]
CLASSICAL7 = ["太陽","水星","金星","火星","木星","土星"]

def jd_of(dt_local, tz):
    u = dt_local.replace(tzinfo=ZoneInfo(tz)).astimezone(ZoneInfo("UTC"))
    return swe.julday(u.year, u.month, u.day, u.hour + u.minute/60 + u.second/3600)

def pos(jd, pid):
    p, _ = swe.calc_ut(jd, pid, swe.FLG_MOSEPH | swe.FLG_SPEED)
    return p[0] % 360, p[3]  # 黃經, 速度

def fmt(lon):
    s = int(lon // 30); d = lon % 30
    return f"{SIGNS[s]}{int(d)}度{int(d%1*60):02d}分", s

def dignity(name, sign):
    if name in DOMICILE and sign in DOMICILE[name]: return "入廟"
    if name in EXALT and sign == EXALT[name]: return "擢升(旺)"
    if name in DOMICILE and (sign+6) % 12 in DOMICILE[name]: return "陷(失勢)"
    if name in EXALT and sign == (EXALT[name]+6) % 12: return "落(弱)"
    return ""

def house_of(lon, cusps):
    for i in range(12):
        a, b = cusps[i], cusps[(i+1) % 12]
        if (a <= lon < b) if a < b else (lon >= a or lon < b):
            return i + 1
    return 12

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date"); ap.add_argument("--electional")
    ap.add_argument("--tz", required=True); ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--house", default="P", choices=["P","W"])
    a = ap.parse_args()

    if a.electional:
        dt = datetime.strptime(a.electional, "%Y-%m-%d %H:%M")
        jd = jd_of(dt, a.tz)
        mlon, mspd = pos(jd, swe.MOON); slon, _ = pos(jd, swe.SUN)
        mtxt, msign = fmt(mlon)
        phase = (mlon - slon) % 360
        ph = ["新月","眉月(漸盈)","上弦","盈凸","滿月","虧凸","下弦","殘月(漸虧)"][int(((phase+22.5)%360)//45)]
        # VOC: 月亮離開本星座前是否還會與古典七政成主相位(掃描法)
        voc, hit = True, None
        jj, end_lon = jd, (msign+1)*30 % 360
        while True:
            ml, _ = pos(jj, swe.MOON)
            if int(ml//30) != msign: break
            for pn in CLASSICAL7:
                pl, _ = pos(jj, dict((n,i) for n,i in PLANETS)[pn])
                for ang, an, _o in ASPECTS:
                    d = abs((ml - pl) % 360); d = min(d, 360-d)
                    if abs(d - ang) < 0.15:
                        voc, hit = False, f"月亮將{an}{pn}"
                        break
                if not voc: break
            if not voc: break
            jj += 15/1440.0
        retro = []
        for n, pid in PLANETS[2:10]:
            _, spd = pos(jd, pid)
            if spd < 0: retro.append(n)
        print(json.dumps({"擇日時間": a.electional, "月亮": mtxt, "月相": ph + f"(日月夾角{round(phase)}度)",
            "月空亡VOC": "是(此時段不宜啟動新事)" if voc else f"否({hit})",
            "逆行行星": retro or ["無"],
            "註": "擇日占星細則見 references/electional.md"}, ensure_ascii=False, indent=1)); return

    dt = datetime.strptime(a.date, "%Y-%m-%d %H:%M")
    jd = jd_of(dt, a.tz)
    cusps_p, ascmc = swe.houses(jd, a.lat, a.lon, b'P')
    asc_txt, asc_sign = fmt(ascmc[0]); mc_txt, _ = fmt(ascmc[1])
    cusps = list(cusps_p) if a.house == "P" else [asc_sign*30 + i*30 for i in range(12)]

    plist, lons = [], {}
    for n, pid in PLANETS:
        lon, spd = pos(jd, pid); lons[n] = lon
        txt, sg = fmt(lon)
        plist.append({"行星": n, "位置": txt, "宮位": house_of(lon, cusps),
                      "逆行": spd < 0 and n not in ("太陽","月亮"), "尊貴": dignity(n, sg)})
    st, _ = fmt((lons["北交點"]+180) % 360)
    plist.append({"行星": "南交點", "位置": st, "宮位": house_of((lons["北交點"]+180)%360, cusps), "逆行": False, "尊貴": ""})

    asp = []
    keys = [n for n,_ in PLANETS]
    for i in range(len(keys)):
        for j in range(i+1, len(keys)):
            d = abs((lons[keys[i]] - lons[keys[j]]) % 360); d = min(d, 360-d)
            for ang, an, orb in ASPECTS:
                if abs(d - ang) <= orb:
                    asp.append(f"{keys[i]} {an} {keys[j]}(容許度{round(abs(d-ang),1)})")
    print(json.dumps({"出生資料": {"當地時間": a.date, "時區": a.tz, "緯度": a.lat, "經度": a.lon},
        "宮位制": "Placidus" if a.house=="P" else "整宮制",
        "上升ASC": asc_txt, "天頂MC": mc_txt,
        "行星": plist, "相位": asp}, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
