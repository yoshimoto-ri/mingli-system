#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
曆法換算工具:陽曆 -> 真太陽時 -> 時辰 -> 農曆/干支
規則:
- 一律以出生地當地時間輸入,依 IANA 時區自動處理日光節約時間(DST)
- 真太陽時 = 標準時 + 經度修正((當地經度-時區中央經線)*4分) + 均時差(NOAA)
- 子時規則:真太陽時 >= 23:00 視為「次日」之早子時(子時為一日之始)
用法:
  python3 convert.py --date "1990-08-15 23:15" --tz "Asia/Taipei" --lon 121.56
  可選: --no-tst 不做真太陽時校正(僅DST)
        --lat 出生地緯度(提供時加算上升星座交界)
  輸出含「邊界對照」:八字年/月界、紫微年/月界、時辰界、太陽/上升換座的距離與警示
輸出: JSON
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

_ensure("lunar-python", "lunar_python")
_ensure("pyswisseph", "swisseph")
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from boundaries import boundary_table
from lunar_python import Solar
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

SHICHEN = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

def equation_of_time(dt_utc):
    """均時差(分鐘), NOAA 近似式, 誤差 < 0.5 分鐘"""
    day_of_year = dt_utc.timetuple().tm_yday
    frac_hour = dt_utc.hour + dt_utc.minute / 60.0
    gamma = 2 * math.pi / 365.0 * (day_of_year - 1 + (frac_hour - 12) / 24.0)
    eot = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
                    - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))
    return eot

def shichen_of(dt):
    """回傳 (時辰名, iztro time_index, 排盤用日期dt)。>=23:00 進次日早子時"""
    h = dt.hour
    if h >= 23:
        return "子", 0, (dt + timedelta(hours=1)).replace(hour=0)  # 次日
    # 查表(不計算)
    _HOUR_TO_SC = {0:0,1:1,2:1,3:2,4:2,5:3,6:3,7:4,8:4,9:5,10:5,
                   11:6,12:6,13:7,14:7,15:8,16:8,17:9,18:9,19:10,20:10,21:11,22:11}
    idx = _HOUR_TO_SC[h]
    return SHICHEN[idx], idx, dt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help='當地時間 "YYYY-MM-DD HH:MM"')
    ap.add_argument("--tz", required=True, help='IANA 時區, 如 Asia/Taipei')
    ap.add_argument("--lon", type=float, default=None, help="出生地經度(東經正/西經負)")
    ap.add_argument("--no-tst", action="store_true", help="不做真太陽時校正")
    ap.add_argument("--lat", type=float, default=None, help="出生地緯度(選填,用於上升星座交界)")
    a = ap.parse_args()

    local = datetime.strptime(a.date, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(a.tz))
    utc_offset = local.utcoffset().total_seconds() / 3600.0
    dst = bool(local.dst() and local.dst().total_seconds() != 0)

    tst = local.replace(tzinfo=None)
    corr_lon_min = corr_eot_min = 0.0
    if not a.no_tst:
        if a.lon is None:
            print(json.dumps({"error": "真太陽時校正需提供 --lon 經度,或改用 --no-tst"}, ensure_ascii=False))
            sys.exit(1)
        meridian = utc_offset * 15.0
        corr_lon_min = (a.lon - meridian) * 4.0
        corr_eot_min = equation_of_time(local.astimezone(ZoneInfo("UTC")))
        tst = local.replace(tzinfo=None) + timedelta(minutes=corr_lon_min + corr_eot_min)

    sc_name, time_index, chart_dt = shichen_of(tst)

    # 農曆(以排盤基準日,含子時換日規則)
    sol = Solar.fromYmdHms(chart_dt.year, chart_dt.month, chart_dt.day,
                           chart_dt.hour, chart_dt.minute, 0)
    lun = sol.getLunar()
    ec = lun.getEightChar()  # 八字四柱(年柱以立春為界)

    out = {
        "輸入當地時間": a.date, "時區": a.tz, "UTC偏移": utc_offset, "日光節約時間": dst,
        "經度修正分鐘": round(corr_lon_min, 1), "均時差分鐘": round(corr_eot_min, 1),
        "真太陽時": tst.strftime("%Y-%m-%d %H:%M"),
        "時辰": sc_name + "時", "iztro_time_index": time_index,
        "換日規則": "真太陽時>=23:00已進次日" if tst.date() != chart_dt.date() else "未換日",
        "排盤基準陽曆": chart_dt.strftime("%Y-%m-%d"),
        "農曆": lun.toString(),
        "閏月": lun.getMonth() < 0,
        "四柱八字_立春界": " ".join([ec.getYear(), ec.getMonth(), ec.getDay(), ec.getTime()]),
        "年干支_正月初一界": lun.getYearInGanZhi(),
        "節氣": lun.getPrevJieQi(True).getName() + "後",
        "生肖": {"鼠":"鼠","牛":"牛","虎":"虎","兔":"兔","龙":"龍","蛇":"蛇","马":"馬","羊":"羊","猴":"猴","鸡":"雞","狗":"狗","猪":"豬"}.get(lun.getYearShengXiao(), lun.getYearShengXiao()),
    }
    out["邊界對照"] = boundary_table(local.replace(tzinfo=None), a.tz,
                                    tst=None if a.no_tst else tst, lat=a.lat, lon=a.lon)
    print(json.dumps(out, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
