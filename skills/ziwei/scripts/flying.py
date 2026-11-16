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
    向心自化:宮干所化之星坐對宮(能量直衝入對宮)
    忌轉忌:A 化忌入 B → B 宮干轉忌入 C → …,預設追 3 層(school.json「忌轉忌層數」)
      每層標註:沖我宮、遇生年忌(雙忌)、自化忌、回到起點;預設遇「自化忌、循環」才提前結束(可設定)
    得失訊號:他宮祿入我宮=得、他宮忌入我宮=勞、忌沖我宮=失
- 我宮:命、財帛、官祿、疾厄、田宅、福德;他宮:兄弟、夫妻、子女、僕役、父母、遷移
"""
import ziwei_rules as R

WO = {"命宮", "財帛", "官祿", "疾厄", "田宅", "福德"}   # 我宮

QT18 = {"紫微", "天機", "太陽", "武曲", "天同", "廉貞", "天府", "太陰", "貪狼", "巨門",
        "天相", "天梁", "七殺", "破軍", "左輔", "右弼", "文昌", "文曲"}

def flying_table(sc):
    t = dict(R.SIHUA_DEFAULT)                    # 全集版 = 欽天門
    t.update(sc.get("飛化層四化覆寫") or {})
    return t

def build(chart, year_gan, sc, depth_override=None):
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

    out_rows, incoming, self_hua, diffs, signals = [], {i: [] for i in range(12)}, [], [], []
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
                self_hua.append(f"{lab(i)} 離心自化{hua}({star})")
            elif j == R.chong(i):
                self_hua.append(f"{lab(i)}→{lab(j)} 向心自化{hua}({star},由{names[i]}直衝入{names[j]})")
            if j != i and names[i] not in WO:
                if hua == "祿" and names[j] in WO:
                    signals.append(f"得:{names[i]}(他宮)祿入{names[j]}(我宮)")
                if hua == "忌" and names[j] in WO:
                    signals.append(f"勞:{names[i]}(他宮)忌入{names[j]}(我宮)")
            if hua == "忌" and names[R.chong(j)] in WO and j != i:
                signals.append(f"失:{names[i]}忌入{names[j]},沖{names[R.chong(j)]}(我宮)")
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
    depth = int(depth_override or cfg.get("忌轉忌層數", 3))
    born_ji_star = ft[year_gan][3]
    born_ji_idx = chart.star_idx.get(born_ji_star)

    def ji_target(i):
        return chart.star_idx.get(ft[stems[i]][3])

    stops = set(cfg.get("轉忌停止條件", ["自化忌", "循環"]))

    def chain(start, first=None, label=None):
        """start:發忌之宮(生年忌為 None);first:已知第一落點。每一層標註事件,遇停止條件才結束"""
        nodes, nxt, reason = [], (first if first is not None else ji_target(start)), None
        for layer in range(1, depth + 1):
            if nxt is None:
                reason = "忌星未入盤"; break
            marks, hit = [], None
            if names[R.chong(nxt)] in WO:
                marks.append(f"沖{names[R.chong(nxt)]}")
                if "忌沖我宮" in stops: hit = f"忌沖我宮({names[R.chong(nxt)]})"
            if born_ji_idx == nxt and not (start is None and layer == 1):
                marks.append("遇生年忌=雙忌")
                if "生年忌" in stops and not hit: hit = "遇生年忌(雙忌)"
            if start is not None and nxt == start and layer > 1:
                marks.append("回到起點")
                if "循環" in stops and not hit: hit = "回到起點(循環)"
            t = ji_target(nxt)
            if t == nxt:
                marks.append("自化忌")
                if "自化忌" in stops and not hit: hit = "自化忌(能量散逸)"
            nodes.append(lab(nxt) + (f"[{'、'.join(marks)}]" if marks else ""))
            if hit:
                reason = hit; break
            nxt = t
        head = label or lab(start)
        return f"{head} → " + " → ".join(nodes) + f"(結束:{reason or f'追滿{depth}層'})"

    ji_chains = [chain(None, born_ji_idx, f"生年{born_ji_star}忌")] if born_ji_idx is not None else []
    ji_chains += [chain(i) for i in range(12)]
    return {
        "四化表": "全集版(欽天門)" + ("+覆寫" if sc.get("飛化層四化覆寫") else ""),
        "來因宮": lab(laiyin) if laiyin is not None else "無",
        "生年四化": born,
        "十二宮飛化": out_rows,
        "自化": self_hua or ["無"],
        "化入": {lab(i): v for i, v in incoming.items() if v},
        "得失訊號": signals or ["無"],
        "忌轉忌": {"層數": depth, "提前結束條件": sorted(stops), "鏈": ji_chains},
        "與中州層差異": diffs or ["無"],
        "說明": "飛化層只論 18 顆星,不論廟旺、煞星、雜曜。祿權忌兩派十干全同,差異僅戊庚壬之化科,見『與中州層差異』。自化與得失僅表能量流向,須法象回生年四化才能定吉凶規模。",
    }
