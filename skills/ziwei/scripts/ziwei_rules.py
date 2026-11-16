# -*- coding: utf-8 -*-
"""
紫微斗數安星規則(獨立實作,不依賴 py-iztro)
用途:
  1. 第二引擎交叉驗證:命身宮、五行局、十四主星、六吉六煞、祿存天馬、生年四化
  2. 流月干支校正:五虎遁 + 農曆月(引擎以節氣月取干,與農曆月宮位口徑不一致)
  3. 斗君/流月命宮驗證
所有索引一律以「寅=0」起算(與 py-iztro 宮位索引一致)。
規則依《紫微斗數全書》通行安法;門派差異以 school.json 覆寫。
"""
from lunar_python.util import LunarUtil

BR = "寅卯辰巳午未申酉戌亥子丑"          # 寅=0
ZHI = "子丑寅卯辰巳午未申酉戌亥"         # 子=0(時辰序)
GAN = "甲乙丙丁戊己庚辛壬癸"

def bi(branch):          # 地支 → 寅=0 索引
    return BR.index(branch)

def chong(i):            # 對宮(沖)
    return (i + 6) % 12

# 十干四化(祿權科忌)——《全書》通行表,與 py-iztro default 相同;門派差異由 school.json 覆寫
SIHUA_DEFAULT = {
    "甲": ["廉貞", "破軍", "武曲", "太陽"],
    "乙": ["天機", "天梁", "紫微", "太陰"],
    "丙": ["天同", "天機", "文昌", "廉貞"],
    "丁": ["太陰", "天同", "天機", "巨門"],
    "戊": ["貪狼", "太陰", "右弼", "天機"],
    "己": ["武曲", "貪狼", "天梁", "文曲"],
    "庚": ["太陽", "武曲", "太陰", "天同"],
    "辛": ["巨門", "太陽", "文曲", "文昌"],
    "壬": ["天梁", "紫微", "左輔", "武曲"],
    "癸": ["破軍", "巨門", "太陰", "貪狼"],
}
HUA = ["祿", "權", "科", "忌"]

# 五虎遁:年干 → 寅月(正月)天干
_WUHU = {"甲": "丙", "己": "丙", "乙": "戊", "庚": "戊", "丙": "庚", "辛": "庚",
         "丁": "壬", "壬": "壬", "戊": "甲", "癸": "甲"}

def month_stem(year_gan, lunar_month):
    """農曆月(1-12)之月干(五虎遁)。"""
    g0 = GAN.index(_WUHU[year_gan])
    return GAN[(g0 + lunar_month - 1) % 10]

def palace_stem(year_gan, idx):
    """宮干:寅宮起五虎遁,順排。"""
    return month_stem(year_gan, idx + 1)

def effective_month(month, day, is_leap, rule="split"):
    """閏月處理。split:前半(1-15)屬本月,後半屬下月(py-iztro fix_leap 口徑);
    same:整個閏月屬本月;next:整個閏月屬下月。回傳 (月, 是否跨入次年正月)"""
    if not is_leap:
        return month, False
    if rule == "same" or (rule == "split" and day <= 15):
        return month, False
    m = month + 1
    return (1, True) if m > 12 else (m, False)

_JU = {"水": 2, "木": 3, "金": 4, "土": 5, "火": 6}
_JU_NAME = {2: "水二局", 3: "木三局", 4: "金四局", 5: "土五局", 6: "火六局"}

def wuxing_ju(ganzhi):
    ny = LunarUtil.NAYIN[ganzhi]
    return _JU[ny[-1]], ny

def ziwei_pos(day, ju):
    """紫微星位置:日數除局數,補數奇退偶進。"""
    k = 0
    while (day + k) % ju:
        k += 1
    q = (day + k) // ju
    return (q - 1 + (k if k % 2 == 0 else -k)) % 12

def place_stars(year_gan, year_zhi, month, day, hour):
    """month: 已處理閏月之農曆月(1-12);hour: 時辰序 子=0..亥=11。
    回傳 {星名: 寅=0索引},以及 meta。"""
    ming = (month - 1 - hour) % 12
    shen = (month - 1 + hour) % 12
    ming_gz = palace_stem(year_gan, ming) + BR[ming]
    ju, nayin = wuxing_ju(ming_gz)
    z = ziwei_pos(day, ju)
    f = (-z) % 12
    s = {}
    # 紫微系(逆)
    s.update({"紫微": z, "天機": (z-1) % 12, "太陽": (z-3) % 12, "武曲": (z-4) % 12,
              "天同": (z-5) % 12, "廉貞": (z-8) % 12})
    # 天府系(順)
    s.update({"天府": f, "太陰": (f+1) % 12, "貪狼": (f+2) % 12, "巨門": (f+3) % 12,
              "天相": (f+4) % 12, "天梁": (f+5) % 12, "七殺": (f+6) % 12, "破軍": (f+10) % 12})
    # 時系
    s["文昌"] = (bi("戌") - hour) % 12
    s["文曲"] = (bi("辰") + hour) % 12
    s["地劫"] = (bi("亥") + hour) % 12
    s["地空"] = (bi("亥") - hour) % 12
    # 月系
    s["左輔"] = (bi("辰") + month - 1) % 12
    s["右弼"] = (bi("戌") - (month - 1)) % 12
    # 年干系
    lucun = {"甲": "寅", "乙": "卯", "丙": "巳", "戊": "巳", "丁": "午", "己": "午",
             "庚": "申", "辛": "酉", "壬": "亥", "癸": "子"}[year_gan]
    s["祿存"] = bi(lucun)
    s["擎羊"] = (bi(lucun) + 1) % 12
    s["陀羅"] = (bi(lucun) - 1) % 12
    kui, yue = {"甲": "丑未", "戊": "丑未", "庚": "丑未", "乙": "子申", "己": "子申",
                "丙": "亥酉", "丁": "亥酉", "辛": "午寅", "壬": "卯巳", "癸": "卯巳"}[year_gan]
    s["天魁"], s["天鉞"] = bi(kui), bi(yue)
    # 年支系
    grp = {"寅": 0, "午": 0, "戌": 0, "申": 1, "子": 1, "辰": 1,
           "巳": 2, "酉": 2, "丑": 2, "亥": 3, "卯": 3, "未": 3}[year_zhi]
    s["天馬"] = bi(["申", "寅", "亥", "巳"][grp])
    huo0, ling0 = [("丑", "卯"), ("寅", "戌"), ("卯", "戌"), ("酉", "戌")][grp]
    s["火星"] = (bi(huo0) + hour) % 12
    s["鈴星"] = (bi(ling0) + hour) % 12
    meta = {"命宮": ming, "身宮": shen, "命宮干支": ming_gz, "五行局": _JU_NAME[ju], "納音": nayin}
    return s, meta

def dou_jun_first_month(year_branch_idx, ming_idx):
    """斗君(流年正月宮)= 流年太歲宮 逆數生月、順數生時;化簡為 (太歲宮 - 本命命宮)。"""
    return (year_branch_idx - ming_idx) % 12
