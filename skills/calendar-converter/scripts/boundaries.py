# -*- coding: utf-8 -*-
"""
邊界對照表:同一個出生時刻,在各命理系統的「切點」附近有多近。
唯一主軸 = 出生絕對時刻(UTC)。由此同時算:
  太陽黃經 → 立春(八字年界)、節(八字月界)、中氣/星座交界(占星)
  日月合朔 → 農曆月界(紫微月界)、春節(紫微年界)
  真太陽時 → 時辰交界;上升點 → 上升星座交界(占星,需緯度)
天文計算用 Swiss Ephemeris(Moshier,視黃經),時刻以出生地時區輸出。
"""
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import swisseph as swe
from lunar_python import Lunar, Solar

FL = swe.FLG_MOSEPH
SIGNS = ["牡羊","金牛","雙子","巨蟹","獅子","處女","天秤","天蠍","射手","摩羯","水瓶","雙魚"]
# 太陽黃經 0°=春分,每 15° 一節氣
JIEQI = {0:"春分",15:"清明",30:"穀雨",45:"立夏",60:"小滿",75:"芒種",90:"夏至",105:"小暑",120:"大暑",
         135:"立秋",150:"處暑",165:"白露",180:"秋分",195:"寒露",210:"霜降",225:"立冬",240:"小雪",
         255:"大雪",270:"冬至",285:"小寒",300:"大寒",315:"立春",330:"雨水",345:"驚蟄"}
JIE = [l for l in JIEQI if (l - 315) % 30 == 0]   # 節:八字月界
ZHONG = [l for l in JIEQI if l % 30 == 0]         # 中氣:= 太陽換星座

def _jd(dt_utc):
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day,
                      dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600)

def _dt(jd, tz):
    y, m, d, h = swe.revjul(jd)
    return (datetime(y, m, d, tzinfo=ZoneInfo("UTC")) + timedelta(hours=h)).astimezone(ZoneInfo(tz))

def sun_lon(jd):
    return swe.calc_ut(jd, swe.SUN, FL)[0][0] % 360

def moon_lon(jd):
    return swe.calc_ut(jd, swe.MOON, FL)[0][0] % 360

def _sd(a, b):
    return ((a - b + 180) % 360) - 180

def _root(f, a, b):
    fa = f(a)
    for _ in range(60):
        m = (a + b) / 2; fm = f(m)
        if (fm > 0) == (fa > 0): a, fa = m, fm
        else: b = m
        if b - a < 1/86400: break
    return (a + b) / 2

def sun_cross(target, jd, direction):
    """太陽到達黃經 target 的時刻;direction=-1 往前找,+1 往後找"""
    j = jd
    for _ in range(400):
        jn = j + direction
        d0, d1 = _sd(sun_lon(j), target), _sd(sun_lon(jn), target)
        if (d0 > 0) != (d1 > 0) and abs(d0) < 5:
            return _root(lambda x: _sd(sun_lon(x), target), min(j, jn), max(j, jn))
        j = jn
    return None

def new_moon(jd, direction):
    f = lambda x: _sd(moon_lon(x), sun_lon(x))
    j = jd
    for _ in range(80):
        jn = j + direction * 0.5
        d0, d1 = f(j), f(jn)
        if (d0 > 0) != (d1 > 0) and abs(d0) < 30:
            return _root(f, min(j, jn), max(j, jn))
        j = jn
    return None

def _level(hours, high, warn):
    a = abs(hours)
    return "警示" if a < high else ("注意" if a < warn else "安全")

def _fmt_h(h):
    a = abs(h)
    s = f"{a/24:.1f} 天" if a >= 48 else (f"{a:.1f} 小時" if a >= 1 else f"{a*60:.0f} 分鐘")
    return ("已過邊界 " if h >= 0 else "距邊界還有 ") + s   # h = 出生 - 邊界

def _prev_next(seq_lons, jd, tz, names):
    s = sun_lon(jd)
    prev_t = min(seq_lons, key=lambda l: (s - l) % 360)
    next_t = min(seq_lons, key=lambda l: (l - s) % 360)
    jp, jn = sun_cross(prev_t, jd, -1), sun_cross(next_t, jd, +1)
    return (names(prev_t), jp), (names(next_t), jn)

def boundary_table(local_dt, tz, tst=None, lat=None, lon=None):
    """local_dt: 出生當地鐘錶時間(naive);tst: 真太陽時(naive,選填);回傳 dict"""
    u = local_dt.replace(tzinfo=ZoneInfo(tz)).astimezone(ZoneInfo("UTC"))
    jd = _jd(u)
    rows, notes = [], []
    T = lambda j: _dt(j, tz).strftime("%Y-%m-%d %H:%M")

    def add(sys_, name, prev, nxt, high, warn, meaning):
        (pn, jp), (nn, jn) = prev, nxt
        hp, hn = (jd - jp)*24, (jd - jn)*24
        near_h = hp if abs(hp) < abs(hn) else hn
        lv = _level(near_h, high, warn)
        rows.append({"系統": sys_, "邊界": name,
                     "前一界": f"{pn} {T(jp)}", "後一界": f"{nn} {T(jn)}",
                     "距最近邊界": _fmt_h(near_h), "狀態": lv, "影響": meaning})
        return lv, near_h

    # 1 八字年界:立春
    lv_y, _ = add("八字", "年柱(立春)", *_prev_next([315], jd, tz, lambda l: "立春"),
                  24, 72, "年柱換干支 → 整組年干十神、納音、生肖(八字口徑)改變")
    # 2 八字月界:節
    lv_m, _ = add("八字", "月柱(節)", *_prev_next(JIE, jd, tz, lambda l: JIEQI[l]),
                  24, 72, "月柱換 → 月令改變,直接影響日主強弱與格局判斷")
    # 3 占星:太陽換座(中氣)
    s = sun_lon(jd)
    lv_s, _ = add("占星/八字", "太陽換座(中氣)", *_prev_next(ZHONG, jd, tz,
                  lambda l: f"{JIEQI[l]}/入{SIGNS[l//30]}"),
                  24, 48, "太陽星座改變;八字為月中(中氣)不換柱")

    # 4 紫微年界:春節(正月初一,以中國標準時曆日)
    base = tst or local_dt
    lun = Solar.fromYmdHms(base.year, base.month, base.day, base.hour, base.minute, 0).getLunar()
    ly = lun.getYear()
    cny_prev = Lunar.fromYmd(ly, 1, 1).getSolar()
    cny_next = Lunar.fromYmd(ly + 1, 1, 1).getSolar()
    d_prev = (base.date() - datetime(cny_prev.getYear(), cny_prev.getMonth(), cny_prev.getDay()).date()).days
    d_next = (base.date() - datetime(cny_next.getYear(), cny_next.getMonth(), cny_next.getDay()).date()).days
    near_d = d_prev if abs(d_prev) <= abs(d_next) else d_next
    lv_c = "警示" if abs(near_d) <= 1 else ("注意" if abs(near_d) <= 3 else "安全")
    rows.append({"系統": "紫微", "邊界": "年界(正月初一)",
                 "前一界": f"春節 {cny_prev.toYmd()}", "後一界": f"春節 {cny_next.toYmd()}",
                 "距最近邊界": ("已過邊界 " if near_d >= 0 else "距邊界還有 ") + f"{abs(near_d)} 天", "狀態": lv_c,
                 "影響": "生年干換 → 生年四化、祿存羊陀、魁鉞等年系星全部改變"})

    # 5 紫微月界:合朔(農曆初一)
    jp, jn = new_moon(jd, -1), new_moon(jd, +1)
    hp, hn = (jd - jp)*24, (jd - jn)*24
    nh = hp if abs(hp) < abs(hn) else hn
    lv_n = _level(nh, 12, 36)
    leap = lun.getMonth() < 0
    rows.append({"系統": "紫微", "邊界": "月界(合朔/初一)",
                 "前一界": f"朔 {T(jp)}", "後一界": f"朔 {T(jn)}",
                 "距最近邊界": _fmt_h(nh), "狀態": lv_n,
                 "影響": "農曆月或日改變 → 命宮/身宮(月)、紫微星位置(日)改變"
                         + (";此月為閏月,依 school.json 閏月規則" if leap else "")})
    if leap and lun.getDay() in (15, 16):
        rows.append({"系統": "紫微", "邊界": "閏月前後半(15/16日)", "前一界": "", "後一界": "",
                     "距最近邊界": f"閏月{lun.getDay()}日", "狀態": "警示",
                     "影響": "閏月以15/16日切分歸屬月份,時辰換日或門派不同即換月 → 命身宮改變"})
    if leap:
        notes.append(f"出生在閏{abs(lun.getMonth())}月{lun.getDay()}日:紫微依閏月規則判月(預設前半屬本月、後半屬下月),不同門派可能排出不同命宮")

    # 6 時辰界(真太陽時)
    if tst:
        mins = tst.hour*60 + tst.minute
        edges = [(h*60) for h in range(-1, 25, 2)]
        e = min(edges, key=lambda x: abs(mins - x))
        dm = mins - e
        lv_t = "警示" if abs(dm) < 10 else ("注意" if abs(dm) < 30 else "安全")
        hh = (e // 60) % 24
        rows.append({"系統": "紫微/八字", "邊界": "時辰(真太陽時)",
                     "前一界": "", "後一界": "",
                     "距最近邊界": f"距 {hh:02d}:00 交界 {'後' if dm >= 0 else '前'} {abs(dm)} 分鐘", "狀態": lv_t,
                     "影響": "時辰改變 → 紫微命身宮與時系星、八字時柱全部改變"
                             + (";23:00 交界另涉子時換日" if hh == 23 else "")})

    # 7 上升星座(需緯度)
    if lat is not None and lon is not None:
        _, ascmc = swe.houses(jd, lat, lon, b'P')
        asc = ascmc[0] % 360
        deg = asc % 30
        near = min(deg, 30 - deg)
        lv_a = "警示" if near < 1 else ("注意" if near < 3 else "安全")
        mins = near * 4  # 上升點約每 4 分鐘移動 1 度(粗估)
        rows.append({"系統": "占星", "邊界": "上升星座",
                     "前一界": "", "後一界": "",
                     "距最近邊界": f"上升 {SIGNS[int(asc//30)]}{deg:.1f}°,距交界 {near:.1f}°(約出生時間 {mins:.0f} 分鐘)",
                     "狀態": lv_a, "影響": "上升星座改變 → 整組宮主星與宮位改變"})
    m = moon_lon(jd); md = m % 30
    if min(md, 30 - md) < 1:
        notes.append(f"月亮在{SIGNS[int(m//30)]}{md:.1f}°,接近換座(月亮約每 2 小時移 1°)")

    # 口徑差異:八字年 vs 紫微年
    ec_y = lun.getEightChar().getYear()
    zw_y = lun.getYearInGanZhi()
    if ec_y != zw_y:
        notes.append(f"出生落在立春與春節之間:八字年柱 {ec_y}、紫微生年 {zw_y}。屬正常口徑差異,兩系統各用各的,不可混用")
    flagged = [r for r in rows if r["狀態"] != "安全"]
    summary = "全部安全" if not flagged else "、".join(f"{r['系統']}{r['邊界']}({r['狀態']})" for r in flagged)
    return {"主軸": f"出生時刻 UTC {u.strftime('%Y-%m-%d %H:%M')}(各系統邊界皆由此推算)",
            "摘要": summary, "對照表": rows, "口徑提示": notes or ["無"],
            "判讀原則": "警示=出生時間誤差或門派口徑可能讓該系統換柱/換宮,須確認或兩案並看;注意=交接期,論命可參酌前後氣;安全=遠離邊界"}
