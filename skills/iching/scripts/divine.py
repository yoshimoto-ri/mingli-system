#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
易經卜卦(文王卦六爻 + 梅花易數)
文王卦(搖卦):  python3 divine.py --method liuyao --datetime "2026-06-11 21:30" --tz Asia/Taipei
  指定爻象:      加 --lines 788697  (由初爻至上爻; 6老陰 7少陽 8少陰 9老陽)
梅花(時間起卦): python3 divine.py --method meihua --datetime "2026-06-11 21:30" --tz Asia/Taipei
梅花(數字起卦): 加 --numbers "17,32"(二數:上/下卦, 動爻=和+時辰數) 或 "17,32,5"(三數)
輸出 JSON; 月建日辰以節氣月/日干支為準, 供旺衰判斷
"""
import argparse, json, secrets, sys, subprocess
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

_ensure("lunar-python", "lunar_python")
from lunar_python import Solar
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

# ---------- 基礎表 ----------
TRI_BITS = {"乾":(1,1,1),"兌":(1,1,0),"離":(1,0,1),"震":(1,0,0),"巽":(0,1,1),"坎":(0,1,0),"艮":(0,0,1),"坤":(0,0,0)}
BITS_TRI = {v:k for k,v in TRI_BITS.items()}
XIANTIAN = {1:"乾",2:"兌",3:"離",4:"震",5:"巽",6:"坎",7:"艮",8:"坤"}  # 先天卦數
NAME = {}  # (上,下)->卦名
_rows = {"乾":"乾為天 天澤履 天火同人 天雷无妄 天風姤 天水訟 天山遯 天地否",
 "兌":"澤天夬 兌為澤 澤火革 澤雷隨 澤風大過 澤水困 澤山咸 澤地萃",
 "離":"火天大有 火澤睽 離為火 火雷噬嗑 火風鼎 火水未濟 火山旅 火地晉",
 "震":"雷天大壯 雷澤歸妹 雷火豐 震為雷 雷風恆 雷水解 雷山小過 雷地豫",
 "巽":"風天小畜 風澤中孚 風火家人 風雷益 巽為風 風水渙 風山漸 風地觀",
 "坎":"水天需 水澤節 水火既濟 水雷屯 水風井 坎為水 水山蹇 水地比",
 "艮":"山天大畜 山澤損 山火賁 山雷頤 山風蠱 山水蒙 艮為山 山地剝",
 "坤":"地天泰 地澤臨 地火明夷 地雷復 地風升 地水師 地山謙 坤為地"}
_low = ["乾","兌","離","震","巽","坎","艮","坤"]
for up, row in _rows.items():
    for low, nm in zip(_low, row.split()):
        NAME[(up, low)] = nm

NAJIA = {  # 各純卦六爻地支(初->上) 與 內/外卦天干
 "乾":(["子","寅","辰","午","申","戌"],"甲","壬"), "坎":(["寅","辰","午","申","戌","子"],"戊","戊"),
 "艮":(["辰","午","申","戌","子","寅"],"丙","丙"), "震":(["子","寅","辰","午","申","戌"],"庚","庚"),
 "巽":(["丑","亥","酉","未","巳","卯"],"辛","辛"), "離":(["卯","丑","亥","酉","未","巳"],"己","己"),
 "坤":(["未","巳","卯","丑","亥","酉"],"乙","癸"), "兌":(["巳","卯","丑","亥","酉","未"],"丁","丁")}
ZHI_WX = {"子":"水","亥":"水","寅":"木","卯":"木","巳":"火","午":"火","申":"金","酉":"金","辰":"土","戌":"土","丑":"土","未":"土"}
GONG_WX = {"乾":"金","兌":"金","離":"火","震":"木","巽":"木","坎":"水","艮":"土","坤":"土"}
SHENG = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
KE = {"木":"土","土":"水","水":"火","火":"金","金":"木"}
BEASTS = ["青龍","朱雀","勾陳","螣蛇","白虎","玄武"]
BEAST_START = {"甲":0,"乙":0,"丙":1,"丁":1,"戊":2,"己":3,"庚":4,"辛":4,"壬":5,"癸":5}

def hexname(bits):  # bits: tuple of 6 (初->上)
    return NAME[(BITS_TRI[bits[3:]], BITS_TRI[bits[:3]])]

def _build_gong():
    """京房八宮: 純卦起,依序變1..5爻、遊魂(再變4)、歸魂(內卦復原) -> {卦bits:(宮,世爻)}"""
    m = {}
    for g in TRI_BITS:
        pure = TRI_BITS[g] + TRI_BITS[g]
        seq = [(pure, 6)]
        cur = list(pure)
        for i in range(5):
            cur[i] ^= 1
            seq.append((tuple(cur), i + 1))
        cur[3] ^= 1
        seq.append((tuple(cur), 4))            # 遊魂
        cur[0], cur[1], cur[2] = TRI_BITS[g]   # 歸魂
        seq.append((tuple(cur), 3))
        for bits, shi in seq:
            m[bits] = (g, shi)
    return m
GONG = _build_gong()

def zhuang(bits, day_gan, day_xunkong):
    """裝卦: 納甲/六親/六獸/世應"""
    gong, shi = GONG[bits]
    ying = shi - 3 if shi > 3 else shi + 3
    gwx = GONG_WX[gong]
    lower, upper = BITS_TRI[bits[:3]], BITS_TRI[bits[3:]]
    rows, b0 = [], BEAST_START[day_gan]
    for i in range(6):
        tri = lower if i < 3 else upper
        zhis, g_in, g_out = NAJIA[tri]
        zhi = zhis[i] if tri in ("乾","坤") or True else zhis[i]
        zhi = NAJIA[tri][0][i]
        gan = g_in if i < 3 else g_out
        wx = ZHI_WX[zhi]
        if wx == gwx: lq = "兄弟"
        elif SHENG[gwx] == wx: lq = "子孫"
        elif SHENG[wx] == gwx: lq = "父母"
        elif KE[gwx] == wx: lq = "妻財"
        else: lq = "官鬼"
        rows.append({"爻": f"{['初','二','三','四','五','上'][i]}爻",
                     "象": "—" if bits[i] else "- -",
                     "干支": gan + zhi, "五行": wx, "六親": lq,
                     "六獸": BEASTS[(b0 + i) % 6],
                     "世應": "世" if i + 1 == shi else ("應" if i + 1 == ying else ""),
                     "旬空": "空" if zhi in day_xunkong else ""})
    return gong, shi, rows

def toss():
    c = sum(2 if secrets.randbelow(2) else 3 for _ in range(3))
    return {6:6, 7:7, 8:8, 9:9}[c]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True, choices=["liuyao","meihua"])
    ap.add_argument("--datetime", help='"YYYY-MM-DD HH:MM" 使用者當地時間(問卦時刻)')
    ap.add_argument("--tz", default="Asia/Taipei")
    ap.add_argument("--lines", help="六爻由初至上, 如 788697")
    ap.add_argument("--numbers", help="梅花數字起卦, 如 17,32 或 17,32,5")
    ap.add_argument("--birthdate", help="出生陽曆 YYYY-MM-DD, 用於計算命主生肖/年干支/五行")
    a = ap.parse_args()

    dt = datetime.strptime(a.datetime, "%Y-%m-%d %H:%M") if a.datetime else datetime.now(ZoneInfo(a.tz)).replace(tzinfo=None)
    lun = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0).getLunar()
    yue_jian, day_gz = lun.getMonthInGanZhi(), lun.getDayInGanZhi()
    xk = lun.getDayXunKong()
    # 命主生肖年支五行(若有提供生日)
    ming_info = {}
    if a.birthdate:
        by, bm, bd = [int(x) for x in a.birthdate.split("-")]
        blun = Solar.fromYmd(by, bm, bd).getLunar()
        yr_gz = blun.getYearInGanZhi()
        yr_zhi = blun.getYearZhi()
        yr_gan = blun.getYearGan()
        sx_map = {"子":"鼠","丑":"牛","寅":"虎","卯":"兔","辰":"龍","巳":"蛇","午":"馬","未":"羊","申":"猴","酉":"雞","戌":"狗","亥":"豬"}
        gan_wx = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水"}
        zhi_wx = {"子":"水","丑":"土","寅":"木","卯":"木","辰":"土","巳":"火","午":"火","未":"土","申":"金","酉":"金","戌":"土","亥":"水"}
        ming_info = {"命主年柱": yr_gz, "生肖": sx_map.get(yr_zhi,""), 
                     "年干五行": gan_wx.get(yr_gan,""), "年支五行": zhi_wx.get(yr_zhi,""),
                     "卦象連結": f"命主屬{zhi_wx.get(yr_zhi,'')}({sx_map.get(yr_zhi,'')}),解卦時以此為命主五行基準,與用神/體用/動爻五行對照生剋"}
    base = {"問卦時間": dt.strftime("%Y-%m-%d %H:%M"),
            "月建": yue_jian, "日辰": day_gz, "旬空": xk, **ming_info}

    if a.method == "liuyao":
        ls = [int(c) for c in a.lines] if a.lines else [toss() for _ in range(6)]
        bits = tuple(1 if v in (7, 9) else 0 for v in ls)
        moving = [i + 1 for i, v in enumerate(ls) if v in (6, 9)]
        gong, shi, rows = zhuang(bits, day_gz[0], xk)
        out = {**base, "起卦方式": "指定爻象" if a.lines else "程式擲錢(三枚)",
               "爻值": "".join(map(str, ls)) + "(初→上)",
               "本卦": f"{hexname(bits)}({gong}宮, 世{['初','二','三','四','五','上'][shi-1]}爻)",
               "六爻": rows, "動爻": [f"第{m}爻" for m in moving] or ["無(靜卦)"]}
        if moving:
            vb = tuple(b ^ (1 if (i + 1) in moving else 0) for i, b in enumerate(bits))
            out["變卦"] = hexname(vb)
        print(json.dumps(out, ensure_ascii=False, indent=1)); return

    # 梅花易數
    if a.numbers:
        ns = [int(x) for x in a.numbers.split(",")]
        sc = (dt.hour + 1) // 2 % 12 + 1
        if len(ns) >= 3: u, l, d = ns[0], ns[1], ns[2]
        else: u, l, d = ns[0], ns[1], ns[0] + ns[1] + sc
        how = f"數字起卦 {a.numbers}(動爻含時辰數{sc})" if len(ns) < 3 else f"數字起卦 {a.numbers}"
    else:
        zi = "子丑寅卯辰巳午未申酉戌亥".index(lun.getYearZhi()) + 1
        mo, dd = abs(lun.getMonth()), lun.getDay()
        sc = "子丑寅卯辰巳午未申酉戌亥".index(lun.getTimeZhi()) + 1
        u, l, d = zi + mo + dd, zi + mo + dd + sc, zi + mo + dd + sc
        how = f"年月日時起卦(年支{zi}+月{mo}+日{dd}, 時{sc})"
    up = XIANTIAN[u % 8 or 8]; low = XIANTIAN[l % 8 or 8]; dong = d % 6 or 6
    bits = TRI_BITS[low] + TRI_BITS[up]
    hu = bits[1:4] + bits[2:5]
    vb = tuple(b ^ (1 if i + 1 == dong else 0) for i, b in enumerate(bits))
    ti, yong = (up, low) if dong <= 3 else (low, up)  # 動爻所在為用卦
    print(json.dumps({**base, "起卦方式": how,
        "本卦": hexname(bits), "互卦": hexname(hu), "變卦": hexname(vb),
        "動爻": f"第{dong}爻",
        "體卦": f"{ti}({GONG_WX[ti]})", "用卦": f"{yong}({GONG_WX[yong]})",
        "體用註": "動爻所在之卦為用, 不動者為體; 以五行論體用生剋"},
        ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
