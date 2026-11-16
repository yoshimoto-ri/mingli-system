# -*- coding: utf-8 -*-
"""
欽天飛化層(宮干飛化)
- 四化表:飛化層用欽天門自己的表(《全集》版),與中州層(王亭之)分開設定
- 星曜:欽天門只用 18 顆星(十四主星 + 左輔右弼文昌文曲);全集四化表所化之星皆在其內
- 已實作(各派定義一致的部分):
    來因宮:宮干 = 生年干之宮,子丑兩宮不取
    十二宮飛化:各宮宮干之祿權科忌 → 化入哪一宮、沖哪一宮
    自化:宮干所化之星即坐本宮
    化入:每宮收到哪些宮飛來的四化
- 待定(school.json「飛化設定」):離心/向心自化定義、忌轉忌追蹤層數
"""
import ziwei_rules as R

QT18 = {"紫微", "天機", "太陽", "武曲", "天同", "廉貞", "天府", "太陰", "貪狼", "巨門",
        "天相", "天梁", "七殺", "破軍", "左輔", "右弼", "文昌", "文曲"}

def flying_table(sc):
    t = dict(R.SIHUA_DEFAULT)                    # 全集版 = 欽天門
    t.update(sc.get("飛化層四化覆寫") or {})
    return t

def build(chart, year_gan, sc):
    """chart: chart.Chart(引擎盤);回傳飛化層 dict"""
    r = chart.r
    names = chart.natal_names
    stems = [p.heavenly_stem for p in r.palaces]
    ft = flying_table(sc)
    zt = dict(R.SIHUA_DEFAULT); zt.update(sc.get("四化覆寫") or {})
    lab = lambda i: f"{names[i]}({R.BR[i]})"

    # 來因宮
    lai = [i for i in range(10) if stems[i] == year_gan]   # 寅=0 … 亥=9,不含子丑
    laiyin = lai[0] if lai else None

    out_rows, incoming, self_hua, diffs = [], {i: [] for i in range(12)}, [], []
    for i in range(12):
        g = stems[i]
        row = {"宮": lab(i), "宮干": g}
        for k, star in enumerate(ft[g]):
            hua = R.HUA[k]
            j = chart.star_idx.get(star)
            if j is None or star not in QT18:
                row[hua] = f"{star}(未入盤)"
                continue
            tag = f"{star}→{lab(j)}" + (" 自化" if j == i else f",沖{lab(R.chong(j))}")
            row[hua] = tag
            incoming[j].append(f"{names[i]}{hua}")
            if j == i:
                self_hua.append(f"{lab(i)} 自化{hua}({star})")
            zstar = zt[g][k]
            if zstar != star:
                zj = chart.star_idx.get(zstar)
                diffs.append(f"{lab(i)} 宮干{g}化{hua}:欽天={star}→{lab(j)};中州={zstar}→{lab(zj) if zj is not None else '?'}")
        out_rows.append(row)

    born = []
    for k, star in enumerate(ft[year_gan]):
        j = chart.star_idx.get(star)
        born.append(f"{star}化{R.HUA[k]}→{lab(j)}")

    cfg = sc.get("飛化設定") or {}
    return {
        "四化表": "全集版(欽天門)" + ("+覆寫" if sc.get("飛化層四化覆寫") else ""),
        "來因宮": lab(laiyin) if laiyin is not None else "無",
        "生年四化": born,
        "十二宮飛化": out_rows,
        "自化": self_hua or ["無"],
        "化入": {lab(i): v for i, v in incoming.items() if v},
        "與中州層差異": diffs or ["無"],
        "待定規則": {"離心/向心自化": cfg.get("自化定義", "待定"),
                     "忌轉忌層數": cfg.get("忌轉忌層數", "待定")},
        "說明": "飛化層只論 18 顆星,不論廟旺、煞星、雜曜。祿權忌兩派十干全同,差異僅戊庚壬之化科,見『與中州層差異』。",
    }
