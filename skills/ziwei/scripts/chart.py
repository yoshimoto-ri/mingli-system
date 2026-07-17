#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
紫微斗數排盤(py-iztro 引擎, 繁體輸出)
- 內建真太陽時/DST校正與子時換日規則(同 calendar-converter skill)
- 子時規則: 真太陽時 >= 23:00 視為次日早子時
用法:
  python3 chart.py --date "1990-08-15 23:15" --tz "Asia/Taipei" --lon 121.56 --gender 女
  加流年: --target "2026-06-11"
  已知時辰可直接: --chart-date "1990-08-16" --time-index 0 --gender 女 (跳過校正)
輸出: JSON 命盤
"""
import argparse, json, math, sys, subprocess
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

_ensure("py-iztro", "py_iztro")
_ensure("lunar-python", "lunar_python")
from py_iztro import Astro
from lunar_python import Solar as LSolar
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

SHICHEN = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]

ZHI_SX = {"子":"鼠","丑":"牛","寅":"虎","卯":"兔","辰":"龍","巳":"蛇","午":"馬","未":"羊","申":"猴","酉":"雞","戌":"狗","亥":"豬"}
CHONG = {"子":"午","午":"子","丑":"未","未":"丑","寅":"申","申":"寅","卯":"酉","酉":"卯","辰":"戌","戌":"辰","巳":"亥","亥":"巳"}
S2T = {"鼠":"鼠","牛":"牛","虎":"虎","兔":"兔","龙":"龍","蛇":"蛇","马":"馬","羊":"羊","猴":"猴","鸡":"雞","狗":"狗","猪":"豬"}

def lunar_of(date_str):
    y, m, d = [int(x) for x in date_str.split("-")]
    return LSolar.fromYmd(y, m, d).getLunar()


def eot(dt_utc):
    d = dt_utc.timetuple().tm_yday
    g = 2*math.pi/365.0*(d-1+(dt_utc.hour+dt_utc.minute/60.0-12)/24.0)
    return 229.18*(0.000075+0.001868*math.cos(g)-0.032077*math.sin(g)
                   -0.014615*math.cos(2*g)-0.040849*math.sin(2*g))

def true_solar(date_str, tz, lon):
    local = datetime.strptime(date_str, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(tz))
    off = local.utcoffset().total_seconds()/3600.0
    corr = (lon - off*15.0)*4.0 + eot(local.astimezone(ZoneInfo("UTC")))
    return local.replace(tzinfo=None) + timedelta(minutes=corr)


# 時辰查表(hour→index),取代計算
_HOUR_TO_SC = {
    0:0, 1:1, 2:1, 3:2, 4:2, 5:3, 6:3, 7:4, 8:4, 9:5, 10:5,
    11:6, 12:6, 13:7, 14:7, 15:8, 16:8, 17:9, 18:9,
    19:10, 20:10, 21:11, 22:11
}
def shichen_of(dt):
    """時辰查表(不計算):hour→(index, 排盤日期)"""
    if dt.hour >= 23:
        return 0, (dt + timedelta(hours=1)).replace(hour=0)  # 晚子時進次日
    return _HOUR_TO_SC[dt.hour], dt

def star_s(s):
    t = s.name
    if getattr(s, "brightness", ""): t += f"[{s.brightness}]"
    if getattr(s, "mutagen", ""): t += f"({s.mutagen})"
    return t

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help='出生當地時間 "YYYY-MM-DD HH:MM"')
    ap.add_argument("--tz", help="IANA 時區")
    ap.add_argument("--lon", type=float, help="出生地經度")
    ap.add_argument("--gender", required=True, choices=["男","女"])
    ap.add_argument("--target", help='流年目標日 "YYYY-MM-DD",預設今天', default=None)
    ap.add_argument("--chart-date", help="已校正之排盤陽曆日 YYYY-MM-DD")
    ap.add_argument("--time-index", type=int, help="已校正之時辰索引 0-12")
    a = ap.parse_args()

    meta = {}
    if a.chart_date is not None and a.time_index is not None:
        cd, ti = a.chart_date, a.time_index
    else:
        if not (a.date and a.tz and a.lon is not None):
            print(json.dumps({"error":"需提供 --date --tz --lon,或 --chart-date 加 --time-index"}, ensure_ascii=False)); sys.exit(1)
        tst = true_solar(a.date, a.tz, a.lon)
        ti, cdt = shichen_of(tst)
        cd = cdt.strftime("%Y-%m-%d")
        meta = {"真太陽時": tst.strftime("%Y-%m-%d %H:%M"),
                "子時換日": tst.strftime("%Y-%m-%d") != cd}

    r = Astro().by_solar(cd, ti, a.gender, True, "zh-TW")
    lun_b = lunar_of(cd)
    by = lun_b.getYear()  # 農曆出生年(虛歲基準)
    palaces = []
    for p in r.palaces:
        palaces.append({
            "宮": p.name + ("(身宮)" if p.is_body_palace else ""),
            "干支": p.heavenly_stem + p.earthly_branch,
            "主星": [star_s(s) for s in p.major_stars],
            "輔星": [star_s(s) for s in p.minor_stars],
            "雜曜": [s.name for s in p.adjective_stars],
            "大限": f"{p.decadal.range[0]}-{p.decadal.range[1]}歲({by+p.decadal.range[0]-1}-{by+p.decadal.range[1]-1}年)",
        })
    out = {**meta,
        "排盤基準": {"陽曆": cd, "時辰": SHICHEN[ti%12]+"時", "性別": a.gender},
        "農曆": r.lunar_date, "四柱": r.chinese_date,
        "命主": r.soul, "身主": r.body, "五行局": r.five_elements_class,
        "十二宮": palaces}

    tgt = a.target or datetime.now().strftime("%Y-%m-%d")
    h = r.horoscope(tgt)
    lun_t = lunar_of(tgt)
    ty_zhi = lun_t.getYearZhi()
    sx_self = S2T.get(lun_b.getYearShengXiao(), lun_b.getYearShengXiao())
    sx_tai = ZHI_SX[ty_zhi]; sx_chong = ZHI_SX[CHONG[ty_zhi]]
    fan = "值太歲(偏沖)" if sx_self == sx_tai else ("沖太歲(正沖)" if sx_self == sx_chong else "無")
    leap = "閏" if lun_t.getMonth() < 0 else ""
    out["命主生肖"] = f"{sx_self}(今年虛歲{lun_t.getYear()-by+1}歲)"
    out["流年太歲"] = {"流年干支": lun_t.getYearInGanZhi(), "偏沖(值太歲)生肖": sx_tai,
                      "正沖(歲破)生肖": sx_chong, "命主犯太歲": fan}
    out["運限"] = {"目標日": tgt,
        "目標日農曆": f"{lun_t.getYearInGanZhi()}年{leap}{lun_t.getMonthInChinese()}月{lun_t.getDayInChinese()}",
        "流月農曆月份": f"農曆{leap}{lun_t.getMonthInChinese()}月",
        "大限": {"宮位地支索引": h.decadal.index, "干支": h.decadal.heavenly_stem+h.decadal.earthly_branch, "四化(祿權科忌)": h.decadal.mutagen},
        "流年": {"干支": h.yearly.heavenly_stem+h.yearly.earthly_branch, "宮位地支索引": h.yearly.index, "四化(祿權科忌)": h.yearly.mutagen},
        "流月": {"干支": h.monthly.heavenly_stem+h.monthly.earthly_branch, "宮位地支索引": h.monthly.index, "四化(祿權科忌)": h.monthly.mutagen},
        "流日": {"干支": h.daily.heavenly_stem+h.daily.earthly_branch, "宮位地支索引": h.daily.index, "四化(祿權科忌)": h.daily.mutagen},
        "說明": "宮位地支索引0=寅宮起算;流月宮位以農曆初一換月為界,流月干支以節氣月為界,解讀月份一律以『流月農曆月份』為準"}
    print(json.dumps(out, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
