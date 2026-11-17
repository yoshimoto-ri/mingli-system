#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
紫微斗數排盤 v2(py-iztro 引擎 + 獨立規則引擎交叉驗證,繁體輸出)

口徑(門派)統一由 ../school.json 設定,每次輸出回報。
- 真太陽時 / DST 校正;子時規則:真太陽時 >= 23:00 視為次日早子時
- 年界預設「正月初一」(py-iztro 預設為立春,v1 曾因此在立春~春節間出生者錯用年干)
- 流月干支以「五虎遁 + 農曆月」計算(引擎以節氣月取干,v1 曾因此錯置流月四化)

用法:
  本命 + 運限:  python3 chart.py --date "1990-08-15 23:15" --tz Asia/Taipei --lon 121.56 --gender 女 --target 2026-06-11
  全年流月表:   python3 chart.py --date ... --gender 女 --months 2027      (農曆該年正月~臘月,含閏月)
  已知時辰:     --chart-date 1990-08-16 --time-index 0 (跳過真太陽時校正)
輸出: JSON
"""
import argparse, json, math, os, sys, subprocess
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
from py_iztro.core.models import ConfigModel, YearDivideEnum, AlgorithmEnum
from lunar_python import Solar as LSolar, Lunar as LLunar, LunarYear
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ziwei_rules as R
import flying as FLY

HERE = os.path.dirname(os.path.abspath(__file__))
SCHOOL_PATH = os.path.join(HERE, "..", "school.json")
SHICHEN = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
ZHI_SX = {"子":"鼠","丑":"牛","寅":"虎","卯":"兔","辰":"龍","巳":"蛇","午":"馬","未":"羊","申":"猴","酉":"雞","戌":"狗","亥":"豬"}
CHONG = {"子":"午","午":"子","丑":"未","未":"丑","寅":"申","申":"寅","卯":"酉","酉":"卯","辰":"戌","戌":"辰","巳":"亥","亥":"巳"}
S2T = {"鼠":"鼠","牛":"牛","虎":"虎","兔":"兔","龙":"龍","蛇":"蛇","马":"馬","羊":"羊","猴":"猴","鸡":"雞","狗":"狗","猪":"豬"}
PALACE_ORDER = ["命宮","兄弟","夫妻","子女","財帛","疾厄","遷移","僕役","官祿","田宅","福德","父母"]
# 覆寫設定送入引擎需簡體
T2S = str.maketrans({"陽":"阳","陰":"阴","機":"机","貞":"贞","軍":"军","門":"门","貪":"贪",
                     "輔":"辅","殺":"杀","廟":"庙","擎":"擎","羅":"罗","鈴":"铃"})

# ---------- 口徑 ----------
def load_school():
    with open(SCHOOL_PATH, encoding="utf-8") as f:
        s = json.load(f)
    return {k: v for k, v in s.items() if not k.startswith("_")}

def build_engine(sc):
    a = Astro()
    yd = YearDivideEnum.NORMAL if sc.get("年界", "正月初一") == "正月初一" else YearDivideEnum.EXACT
    hd = YearDivideEnum.NORMAL if sc.get("運限年界", "正月初一") == "正月初一" else YearDivideEnum.EXACT
    alg = AlgorithmEnum.ZHONGZHOU if sc.get("門派") == "中州" else AlgorithmEnum.DEFAULT
    muts = {g: [x.translate(T2S) for x in v] for g, v in (sc.get("四化覆寫") or {}).items()}
    brs = {k.translate(T2S): [x.translate(T2S) for x in v] for k, v in (sc.get("亮度覆寫") or {}).items()}
    a.config(ConfigModel(yearDivide=yd, horoscopeDivide=hd, algorithm=alg, mutagens=muts, brightness=brs))
    return a

def sihua_table(sc):
    t = dict(R.SIHUA_DEFAULT)
    t.update(sc.get("四化覆寫") or {})
    return t

# ---------- 時間 ----------
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

_HOUR_TO_SC = {0:0, 1:1, 2:1, 3:2, 4:2, 5:3, 6:3, 7:4, 8:4, 9:5, 10:5,
               11:6, 12:6, 13:7, 14:7, 15:8, 16:8, 17:9, 18:9, 19:10, 20:10, 21:11, 22:11}
def shichen_of(dt):
    if dt.hour >= 23:
        return 0, (dt + timedelta(hours=1)).replace(hour=0)
    return _HOUR_TO_SC[dt.hour], dt

def boundary_warning(tst):
    """真太陽時距時辰交界 < 10 分鐘 → 警示(出生時間誤差可能換時辰)"""
    mins = tst.hour*60 + tst.minute
    edge = min(abs(mins - (h*60)) for h in range(-1, 25, 2))  # 奇數整點為時辰交界
    return edge < 10

# ---------- 工具 ----------
def star_s(s):
    t = s.name
    if getattr(s, "brightness", ""): t += f"[{s.brightness}]"
    if getattr(s, "mutagen", ""): t += f"({s.mutagen})"
    return t

def names_from_ming(ming_idx):
    """由某層命宮位置推該層十二宮名(逆時針排)。回傳 list[寅=0..]"""
    out = [""]*12
    for k, n in enumerate(PALACE_ORDER):
        out[(ming_idx - k) % 12] = n
    return out

class Chart:
    def __init__(self, r):
        self.r = r
        self.natal_names = [p.name for p in r.palaces]
        self.star_idx = {}
        for i, p in enumerate(r.palaces):
            for s in list(p.major_stars) + list(p.minor_stars):
                self.star_idx[s.name] = i

    def where(self, star, layers):
        """星曜所在宮 + 對宮,標示各層宮名。layers: {"本":names, "限":names, ...}"""
        i = self.star_idx.get(star)
        if i is None:
            return {"坐": "?", "沖": "?"}
        c = R.chong(i)
        fmt = lambda k: R.BR[k] + "(" + "/".join(f"{ly}{nm[k]}" for ly, nm in layers.items()) + ")"
        return {"坐": fmt(i), "沖": fmt(c)}

    def sihua(self, stars, layers):
        return [{"四化": f"{s}化{R.HUA[k]}", **self.where(s, layers)} for k, s in enumerate(stars)]

def flow_stars(stars_by_idx):
    out = {}
    for i, lst in enumerate(stars_by_idx or []):
        for s in lst:
            out[s.name] = R.BR[i]
    return out

# ---------- 交叉驗證 ----------
def verify(r, cd, ti, sc):
    lun = lunar_of(cd)
    m, d, leap = abs(lun.getMonth()), lun.getDay(), lun.getMonth() < 0
    em, _ = R.effective_month(m, d, leap, sc.get("閏月", "split"))
    yg = lun.getYearGan() if sc.get("年界", "正月初一") == "正月初一" else lun.getYearGanByLiChun()
    yz = lun.getYearZhi() if sc.get("年界", "正月初一") == "正月初一" else lun.getYearZhiByLiChun()
    stars, meta = R.place_stars(yg, yz, em, d, ti % 12)
    eng = Chart(r)
    diffs, n = [], 0
    for name, idx in stars.items():
        n += 1
        ei = eng.star_idx.get(name)
        if ei != idx:
            diffs.append(f"{name}: 規則={R.BR[idx]} 引擎={R.BR[ei] if ei is not None else '無'}")
    ming_e = next(i for i, p in enumerate(r.palaces) if p.name == "命宮")
    shen_e = next(i for i, p in enumerate(r.palaces) if p.is_body_palace)
    for lab, a_, b_ in (("命宮", meta["命宮"], ming_e), ("身宮", meta["身宮"], shen_e)):
        n += 1
        if a_ != b_: diffs.append(f"{lab}: 規則={R.BR[a_]} 引擎={R.BR[b_]}")
    n += 1
    if meta["五行局"] != r.five_elements_class:
        diffs.append(f"五行局: 規則={meta['五行局']} 引擎={r.five_elements_class}")
    # 宮干
    for i, p in enumerate(r.palaces):
        n += 1
        if p.heavenly_stem != R.palace_stem(yg, i):
            diffs.append(f"{R.BR[i]}宮干: 規則={R.palace_stem(yg, i)} 引擎={p.heavenly_stem}")
    # 生年四化
    tbl = sihua_table(sc)
    for k, s in enumerate(tbl[yg]):
        n += 1
        i = eng.star_idx.get(s)
        mut = None
        if i is not None:
            for st in list(r.palaces[i].major_stars) + list(r.palaces[i].minor_stars):
                if st.name == s: mut = st.mutagen
        if mut != R.HUA[k]:
            diffs.append(f"生年{s}化{R.HUA[k]}: 引擎標示={mut}")
    note = "" if not diffs else ("若差異僅在魁鉞/天馬/火鈴等門派分歧星,屬口徑差異;主星或命身宮差異則必須查明再解盤。"
                                 if sc.get("門派") == "中州" else "主星/命身宮/四化有差異時,禁止解盤,先查明原因。")
    return {"結果": "通過" if not diffs else "有差異", "比對項數": n, "差異": diffs, "註": note,
            "生年干支": yg + yz, "農曆月(閏月處理後)": em}

# ---------- 主程式 ----------
def natal_block(a, args, sc):
    meta = {}
    if args.chart_date is not None and args.time_index is not None:
        cd, ti = args.chart_date, args.time_index
    else:
        if not (args.date and args.tz and args.lon is not None):
            print(json.dumps({"error": "需提供 --date --tz --lon,或 --chart-date 加 --time-index"}, ensure_ascii=False)); sys.exit(1)
        tst = true_solar(args.date, args.tz, args.lon)
        ti, cdt = shichen_of(tst)
        cd = cdt.strftime("%Y-%m-%d")
        meta = {"真太陽時": tst.strftime("%Y-%m-%d %H:%M"), "子時換日": tst.strftime("%Y-%m-%d") != cd}
        if boundary_warning(tst):
            meta["時辰交界警示"] = "真太陽時距時辰交界不足10分鐘,出生時間若有誤差可能換時辰,請向當事人確認或兩盤並看"
    r = a.by_solar(cd, ti, args.gender, True, "zh-TW")
    return r, cd, ti, meta

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help='出生當地時間 "YYYY-MM-DD HH:MM"')
    ap.add_argument("--tz", help="IANA 時區")
    ap.add_argument("--lon", type=float, help="出生地經度")
    ap.add_argument("--gender", required=True, choices=["男", "女"])
    ap.add_argument("--target", help='運限目標日 "YYYY-MM-DD",預設今天', default=None)
    ap.add_argument("--months", type=int, help="輸出該農曆年正月~臘月流月表(例 2027 = 丁未年)")
    ap.add_argument("--chart-date", help="已校正之排盤陽曆日 YYYY-MM-DD")
    ap.add_argument("--time-index", type=int, help="已校正之時辰索引 0-12")
    ap.add_argument("--flying", action="store_true", help="加輸出欽天飛化層(宮干飛化、自化、來因宮、忌轉忌)")
    ap.add_argument("--ji-depth", type=int, default=None, help="忌轉忌追蹤層數(預設依 school.json,3 層)")
    args = ap.parse_args()

    sc = load_school()
    a = build_engine(sc)
    r, cd, ti, meta = natal_block(a, args, sc)
    ch = Chart(r)
    tbl = sihua_table(sc)
    lun_b = lunar_of(cd)
    by = lun_b.getYear()
    natal_layers = {"本": ch.natal_names}

    palaces = []
    for i, p in enumerate(r.palaces):
        palaces.append({
            "宮": p.name + ("(身宮)" if p.is_body_palace else ""),
            "干支": p.heavenly_stem + p.earthly_branch,
            "主星": [star_s(s) for s in p.major_stars],
            "輔星": [star_s(s) for s in p.minor_stars],
            "雜曜": [s.name for s in p.adjective_stars],
            "大限": f"{p.decadal.range[0]}-{p.decadal.range[1]}歲({by+p.decadal.range[0]-1}-{by+p.decadal.range[1]-1}年)",
        })
    vf = verify(r, cd, ti, sc)
    out = {"口徑": sc, **meta,
           "排盤基準": {"陽曆": cd, "時辰": SHICHEN[ti % 12] + "時", "性別": args.gender},
           "農曆": r.lunar_date, "四柱": r.chinese_date,
           "命主": r.soul, "身主": r.body, "五行局": r.five_elements_class,
           "十二宮": palaces,
           "生年四化": ch.sihua(tbl[vf["生年干支"][0]], natal_layers),
           "交叉驗證": vf}

    ming_idx = next(i for i, n in enumerate(ch.natal_names) if n == "命宮")

    # ---------- 全年流月表 ----------
    # ---------- 欽天飛化層:夜子(真太陽時23-24點)不換日,另排一盤(書頁23) ----------
    fly_ch, fly_vf, fly_note = ch, vf, "與中州層同一張盤"
    if args.flying and meta.get("子時換日"):
        same_day = meta["真太陽時"][:10]
        r_fly = a.by_solar(same_day, 0, args.gender, True, "zh-TW")
        fly_ch, fly_vf = Chart(r_fly), verify(r_fly, same_day, 0, sc)
        fly_note = f"夜子時不換日:另以 {same_day} 子時排盤(中州層已換日為 {cd})"
    if args.flying:
        fly = FLY.build(fly_ch, fly_vf["生年干支"][0], sc, args.ji_depth)
        fly["排盤口徑"] = fly_note
        if fly_ch is not ch:
            fly["交叉驗證"] = fly_vf["結果"] + (f":{fly_vf['差異']}" if fly_vf["差異"] else "")
        fly["原典規則"] = FLY.book_rules(fly_ch, fly_vf["生年干支"][0], sc, fly)
        out["欽天飛化層"] = fly

    if args.months:
        ly = LunarYear.fromYear(args.months)
        yg, yz = ly.getGanZhi()[0], ly.getGanZhi()[1]
        mid = LLunar.fromYmd(args.months, 6, 1).getSolar().toYmd()
        h = r.horoscope(mid)
        dec_names = h.decadal.palace_names
        yb = R.bi(yz)
        year_names = names_from_ming(yb)
        dj = R.dou_jun_first_month(yb, ming_idx)
        rule = sc.get("閏月", "split")
        rows = []
        for lm in ly.getMonthsInYear():
            mnum, leap = abs(lm.getMonth()), lm.getMonth() < 0
            first = LLunar.fromYmd(lm.getYear(), lm.getMonth(), 1).getSolar()
            last = LLunar.fromYmd(lm.getYear(), lm.getMonth(), lm.getDayCount()).getSolar()
            halves = [(1, lm.getDayCount())]
            if leap and rule == "split":
                halves = [(1, 15), (16, lm.getDayCount())]
            for d0, d1 in halves:
                em, _ = R.effective_month(mnum, d0, leap, rule)
                ms = R.month_stem(yg, em)
                pidx = (dj + em - 1) % 12
                mnames = names_from_ming(pidx)
                # 引擎流月宮位核對(取該段第 10 天或段中)
                chk_day = min(d0 + 9, d1)
                eh = r.horoscope(LLunar.fromYmd(lm.getYear(), lm.getMonth(), chk_day).getSolar().toYmd())
                s_from = LLunar.fromYmd(lm.getYear(), lm.getMonth(), d0).getSolar().toYmd()
                s_to = LLunar.fromYmd(lm.getYear(), lm.getMonth(), d1).getSolar().toYmd()
                rows.append({
                    "農曆月": ("閏" if leap else "") + LunarUtil_month(mnum) + "月" + (f"({d0}-{d1}日,依{LunarUtil_month(em)}月論)" if leap else ""),
                    "國曆": f"{s_from} ~ {s_to}",
                    "流月干支": ms + R.BR[em - 1],
                    "流月命宮": f"{R.BR[pidx]}(本命{ch.natal_names[pidx]}/流年{year_names[pidx]})",
                    "流月四化": ch.sihua(tbl[ms], {"本": ch.natal_names, "年": year_names, "月": mnames}),
                    "宮位核對": "一致" if eh.monthly.index == pidx else f"引擎={R.BR[eh.monthly.index]},以規則為準",
                })
        fly_months = None
        if args.flying:
            fly_months = []
            fming = fly_ch.natal_names.index("命宮")
            fdj = R.dou_jun_first_month(yb, fming)
            for row in rows:
                em_row = "正二三四五六七八九十冬臘".index(row["農曆月"].lstrip("閏")[0]) + 1
                m = (fdj + em_row - 1) % 12
                blk = FLY.year_palace_flight(fly_ch, m, sc, "流月")
                fly_months.append({"農曆月": row["農曆月"], **blk})
        out = {"口徑": sc, "排盤基準": out["排盤基準"], "交叉驗證": vf,
               "流年": {"干支": yg + yz, "流年命宮": f"{yz}(本命{ch.natal_names[yb]})",
                        "斗君(正月)": R.BR[dj],
                        "流年四化": ch.sihua(tbl[yg], {"本": ch.natal_names, "限": dec_names, "年": year_names}),
                        "流年流曜": flow_stars(h.yearly.stars)},
               "流月表": rows,
               **({"欽天飛化層": {**out["欽天飛化層"],
                                 "流年": FLY.year_palace_flight(fly_ch, yb, sc, "流年"),
                                 "流月表": fly_months}} if args.flying else {}),
               "說明": "流月干支=五虎遁(流年干)+農曆月;流月命宮=斗君起正月順行。閏月依 school.json『閏月』規則。"}
        print(json.dumps(out, ensure_ascii=False, indent=1)); return

    # ---------- 目標日運限 ----------
    tgt = args.target or datetime.now().strftime("%Y-%m-%d")
    h = r.horoscope(tgt)
    lun_t = lunar_of(tgt)
    ty_zhi = lun_t.getYearZhi()
    sx_self = S2T.get(lun_b.getYearShengXiao(), lun_b.getYearShengXiao())
    sx_tai = ZHI_SX[ty_zhi]; sx_chong = ZHI_SX[CHONG[ty_zhi]]
    fan = "值太歲(偏沖)" if sx_self == sx_tai else ("沖太歲(正沖)" if sx_self == sx_chong else "無")
    leap = lun_t.getMonth() < 0
    lp = "閏" if leap else ""
    out["命主生肖"] = f"{sx_self}(今年虛歲{lun_t.getYear()-by+1}歲)"
    out["流年太歲"] = {"流年干支": lun_t.getYearInGanZhi(), "偏沖(值太歲)生肖": sx_tai,
                      "正沖(歲破)生肖": sx_chong, "命主犯太歲": fan}

    dec_names, year_names = h.decadal.palace_names, h.yearly.palace_names
    yg = lun_t.getYearGan()
    em, _ = R.effective_month(abs(lun_t.getMonth()), lun_t.getDay(), leap, sc.get("閏月", "split"))
    ms = R.month_stem(yg, em)
    dj = R.dou_jun_first_month(R.bi(ty_zhi), ming_idx)
    m_idx = (dj + em - 1) % 12
    mon_names = names_from_ming(m_idx)
    day_names = h.daily.palace_names
    L = {"本": ch.natal_names, "限": dec_names, "年": year_names, "月": mon_names}
    eng_m = h.monthly.heavenly_stem + h.monthly.earthly_branch
    out["運限"] = {
        "目標日": tgt,
        "目標日農曆": f"{lun_t.getYearInGanZhi()}年{lp}{lun_t.getMonthInChinese()}月{lun_t.getDayInChinese()}",
        "流月農曆月份": f"農曆{lp}{lun_t.getMonthInChinese()}月" + (f"(閏月依{LunarUtil_month(em)}月論)" if leap else ""),
        "大限": {"干支": h.decadal.heavenly_stem + h.decadal.earthly_branch,
                 "大限命宮": f"{h.decadal.earthly_branch}(本命{ch.natal_names[h.decadal.index]})",
                 "四化": ch.sihua(h.decadal.mutagen, {"本": ch.natal_names, "限": dec_names}),
                 "大限流曜": flow_stars(h.decadal.stars)},
        "流年": {"干支": h.yearly.heavenly_stem + h.yearly.earthly_branch,
                 "流年命宮": f"{h.yearly.earthly_branch}(本命{ch.natal_names[h.yearly.index]}/大限{dec_names[h.yearly.index]})",
                 "四化": ch.sihua(h.yearly.mutagen, {"本": ch.natal_names, "限": dec_names, "年": year_names}),
                 "流年流曜": flow_stars(h.yearly.stars)},
        "流月": {"干支": ms + R.BR[em - 1],
                 "流月命宮": f"{R.BR[m_idx]}(本命{ch.natal_names[m_idx]}/流年{year_names[m_idx]})",
                 "四化": ch.sihua(tbl[ms], L),
                 "校正": None if eng_m == ms + R.BR[em - 1] else f"引擎原值{eng_m}(節氣月/宮位口徑不一),已依農曆月校正"},
        "流日": {"干支": h.daily.heavenly_stem + h.daily.earthly_branch,
                 "流日命宮": f"{R.BR[h.daily.index]}(本命{ch.natal_names[h.daily.index]})",
                 "四化": ch.sihua(h.daily.mutagen, {"本": ch.natal_names, "年": year_names, "日": day_names})},
    }
    # 宮位疊盤:每個地支在各層是什麼宮、有哪些流曜
    fy, fd = flow_stars(h.yearly.stars), flow_stars(h.decadal.stars)
    out["宮位疊盤"] = [{
        "地支": R.BR[i], "本命": ch.natal_names[i], "大限": dec_names[i], "流年": year_names[i], "流月": mon_names[i],
        "流曜": [k for k, v in {**fd, **fy}.items() if v == R.BR[i]],
    } for i in range(12)]
    if args.flying:
        out["欽天飛化層"]["運限"] = FLY.yunxian(fly_ch, fly_vf["生年干支"][0], sc, ty_zhi, em,
                                              lun_t.getDay(), lun_t.getYear() - by + 1)
    out["說明"] = "地支索引一律寅起;『坐』=四化星所在宮,『沖』=對宮。本/限/年/月/日 = 本命/大限/流年/流月/流日宮名。"
    print(json.dumps(out, ensure_ascii=False, indent=1))

def LunarUtil_month(m):
    return ["正","二","三","四","五","六","七","八","九","十","冬","臘"][m-1]

if __name__ == "__main__":
    main()
