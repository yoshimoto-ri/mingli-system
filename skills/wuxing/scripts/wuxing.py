#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
陰陽五行分析工具
八字五行分布: python3 wuxing.py --bazi "庚午 甲申 癸丑 壬子"
單一干支查詢: python3 wuxing.py --query 庚
生剋關係:     python3 wuxing.py --relation 金,木
輸出 JSON(含藏干、五行統計、日主旺衰粗判;細論見 references/wuxing-theory.md)
"""
import argparse, json

GAN_WX = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水"}
GAN_YY = {g: ("陽" if i % 2 == 0 else "陰") for i, g in enumerate("甲乙丙丁戊己庚辛壬癸")}
ZHI_WX = {"子":"水","丑":"土","寅":"木","卯":"木","辰":"土","巳":"火","午":"火","未":"土","申":"金","酉":"金","戌":"土","亥":"水"}
CANG = {"子":"癸","丑":"己癸辛","寅":"甲丙戊","卯":"乙","辰":"戊乙癸","巳":"丙戊庚","午":"丁己","未":"己丁乙",
        "申":"庚壬戊","酉":"辛","戌":"戊辛丁","亥":"壬甲"}
SHENG = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
KE = {"木":"土","土":"水","水":"火","火":"金","金":"木"}
SEASON_WANG = {"寅":"木","卯":"木","辰":"土","巳":"火","午":"火","未":"土","申":"金","酉":"金","戌":"土","亥":"水","子":"水","丑":"土"}

def rel(a, b):
    if a == b: return "比和"
    if SHENG[a] == b: return f"{a}生{b}"
    if SHENG[b] == a: return f"{b}生{a}"
    if KE[a] == b: return f"{a}剋{b}"
    return f"{b}剋{a}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bazi"); ap.add_argument("--query"); ap.add_argument("--relation")
    a = ap.parse_args()

    if a.query:
        q = a.query
        if q in GAN_WX:
            print(json.dumps({q: f"{GAN_YY[q]}{GAN_WX[q]}"}, ensure_ascii=False)); return
        if q in ZHI_WX:
            print(json.dumps({q: ZHI_WX[q], "藏干": [f"{c}({GAN_WX[c]})" for c in CANG[q]]}, ensure_ascii=False)); return

    if a.relation:
        x, y = a.relation.split(",")
        print(json.dumps({"關係": rel(x, y)}, ensure_ascii=False)); return

    if a.bazi:
        pillars = a.bazi.split()
        cnt = {w: 0.0 for w in "木火土金水"}
        detail = []
        for p in pillars:
            g, z = p[0], p[1]
            cnt[GAN_WX[g]] += 1
            hidden = CANG[z]
            for i, h in enumerate(hidden):
                cnt[GAN_WX[h]] += [1.0, 0.5, 0.3][min(i, 2)]
            detail.append(f"{p}: 干{g}({GAN_WX[g]}) 支{z}藏{'、'.join(h+'('+GAN_WX[h]+')' for h in hidden)}")
        day_master = pillars[2][0] if len(pillars) >= 3 else pillars[0][0]
        dm_wx = GAN_WX[day_master]
        month_zhi = pillars[1][1] if len(pillars) >= 2 else None
        de_ling = month_zhi and (SEASON_WANG[month_zhi] == dm_wx or SHENG[SEASON_WANG[month_zhi]] == dm_wx)
        total = sum(cnt.values())
        out = {"四柱": pillars, "逐柱": detail,
               "五行統計(含藏干加權)": {k: round(v, 1) for k, v in cnt.items()},
               "最旺": max(cnt, key=cnt.get), "最弱": min(cnt, key=cnt.get),
               "日主": f"{day_master}({GAN_YY[day_master]}{dm_wx})",
               "得令": bool(de_ling),
               "旺衰粗判": ("偏強" if (cnt[dm_wx] + cnt[{v:k for k,v in SHENG.items()}[dm_wx]]) / total > 0.45 or de_ling else "偏弱")
                          + "(粗估,正式論喜用神需通根透干細審,見參考文件)"}
        print(json.dumps(out, ensure_ascii=False, indent=1)); return
    print(json.dumps({"error": "需 --bazi / --query / --relation"}, ensure_ascii=False))

if __name__ == "__main__":
    main()
