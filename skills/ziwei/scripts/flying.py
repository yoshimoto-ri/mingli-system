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
      每層標註:沖我宮、遇生年忌(雙忌)、自化忌、回到起點;預設遇「忌沖我宮、自化忌、循環」即結束(可設定)
    化忌吉凶(原典p363):入六內=吉、其對宮受沖=凶;入六外=凶
    另含原典規則:鏡心訣、物相、法象、串聯、天干化合、運限宮干飛化(見 book_rules / yunxian)
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

    stops = set(cfg.get("轉忌停止條件", ["忌沖我宮", "自化忌", "循環"]))

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
        
        "忌轉忌": {"層數": depth, "提前結束條件": sorted(stops), "鏈": ji_chains,
                  "出處": "飛星派通用追忌法(欽天原典僅有生年四化再轉一次之『物相』,見原典規則)"},
        "與中州層差異": diffs or ["無"],
        "說明": "飛化層只論 18 顆星,不論廟旺、煞星、雜曜。祿權忌兩派十干全同,差異僅戊庚壬之化科,見『與中州層差異』。自化與得失僅表能量流向,須法象回生年四化才能定吉凶規模。",
    }


# ======================================================================
# 欽天門原典規則(蔡明宏《紫微斗數 誤悟我十八年》,頁碼為書頁)
# ======================================================================
LIUNEI = {"命宮", "財帛", "官祿", "福德", "田宅", "疾厄"}           # 六內(內吉)p363
SHI = {"命宮", "疾厄", "田宅", "父母", "兄弟", "子女"}              # 實位 p365(其餘為虛)
HEHUA = {"乙": ("庚", "祿"), "庚": ("乙", "祿"), "戊": ("癸", "權"), "癸": ("戊", "權"),
         "丁": ("壬", "科"), "壬": ("丁", "科"), "丙": ("辛", "忌"), "辛": ("丙", "忌")}  # p495
HUA_PAIR = {"祿": "乙庚", "權": "戊癸", "科": "丁壬", "忌": "丙辛"}


def palace_attr(name):
    return ("六內" if name in LIUNEI else "六外") + ("實" if name in SHI else "虛")


def ji_judge(names, j):
    """化忌入 j 宮之吉凶(p363):入六內吉、其對宮受沖為凶;入六外凶"""
    n, c = names[j], names[R.chong(j)]
    if n in LIUNEI:
        return f"入六內{n}=吉;沖{c}=凶"
    return f"入六外{n}=凶"


def book_rules(chart, year_gan, sc, layer):
    """layer: build() 的輸出(取自化清單)。回傳原典規則區塊"""
    r = chart.r
    names = chart.natal_names
    stems = [p.heavenly_stem for p in r.palaces]
    ft = flying_table(sc)
    lab = lambda i: f"{names[i]}({R.BR[i]})"
    loc = chart.star_idx
    born = {R.HUA[k]: (s, loc.get(s)) for k, s in enumerate(ft[year_gan])}

    out = {}
    out["宮位屬性(p363/365)"] = {lab(i): palace_attr(names[i]) for i in range(12)}

    # 化忌吉凶
    ji = []
    s, j = born["忌"]
    if j is not None:
        ji.append(f"生年{s}忌:{ji_judge(names, j)}")
    for i in range(12):
        j = loc.get(ft[stems[i]][3])
        if j is not None and j != i:
            ji.append(f"{names[i]}宮干{stems[i]}忌→{ji_judge(names, j)}")
    out["化忌吉凶(p363)"] = ji

    # 鏡心訣:生年四化坐宮 → 對宮干轉同一化(p425-428)
    # 物相:生年四化坐宮 → 本宮干再轉同一化(p410/428)
    jx, wx = [], []
    for hua, (s, j) in born.items():
        if j is None:
            continue
        k = R.HUA.index(hua)
        c = R.chong(j)
        t1 = loc.get(ft[stems[c]][k])
        t2 = loc.get(ft[stems[j]][k])
        jx.append(f"生年{s}{hua}坐{lab(j)} → 對宮{names[c]}干{stems[c]}轉{ft[stems[c]][k]}{hua} → {lab(t1) if t1 is not None else '?'}")
        wx.append(f"生年{s}{hua}坐{lab(j)} → 本宮干{stems[j]}再轉{ft[stems[j]][k]}{hua} → {lab(t2) if t2 is not None else '?'}"
                  + ("(自化)" if t2 == j else ""))
    out["鏡心訣(p425)"] = jx
    out["物相(p410)"] = wx

    # 法象與串聯:取所有自化(離心+向心)
    selfs = []   # (宮idx, 化, 星, 型)
    for i in range(12):
        for k, s in enumerate(ft[stems[i]]):
            j = loc.get(s)
            if j == i:
                selfs.append((i, R.HUA[k], s, "離心"))
            elif j is not None and j == R.chong(i):
                selfs.append((j, R.HUA[k], s, "向心"))
    fx = []
    for i, hua, s, typ in selfs:
        bs, bj = born[hua]
        fx.append(f"{lab(i)}{typ}自化{hua}({s}) → 法生年{hua}({bs})在{lab(bj) if bj is not None else '?'}")
    out["法象(p447)"] = fx or ["無自化"]
    groups = {}
    for i, hua, s, typ in selfs:
        groups.setdefault(hua, []).append(f"{names[i]}({typ})")
    out["串聯(p459)"] = [f"自化{h}:" + "、".join(v) for h, v in groups.items() if len(v) >= 2] or ["無"]

    # 天干化合(p495/505):某宮干與哪一宮合化出何象
    hh = []
    for i in range(12):
        g = stems[i]
        if g in HEHUA:
            mate, hua = HEHUA[g]
            ms = [names[x] for x in range(10) if stems[x] == mate]  # 子丑同寅卯,取寅~亥
            hh.append(f"{names[i]}({g}) 與 {'、'.join(ms)}({mate}) 合化{hua}")
    out["天干化合(p495)"] = hh
    return out


def year_palace_flight(chart, idx, sc, tag):
    """以 idx 宮之宮干飛四化(欽天:流年/流月/流日皆用所在宮之宮干,p87)"""
    names = chart.natal_names
    g = chart.r.palaces[idx].heavenly_stem
    ft = flying_table(sc)
    res = []
    for k, s in enumerate(ft[g]):
        j = chart.star_idx.get(s)
        t = f"{s}化{R.HUA[k]}→{names[j]}({R.BR[j]})" if j is not None else f"{s}化{R.HUA[k]}(未入盤)"
        if k == 3 and j is not None:
            t += f"[{ji_judge(names, j)}]"
        res.append(t)
    # 宮位重疊:該宮是否坐生年四化
    return {f"{tag}宮": f"{names[idx]}({R.BR[idx]})", "宮干": g, "四化": res}


def yunxian(chart, year_gan, sc, lunar_year_zhi, eff_month, lunar_day, xusui):
    """欽天飛化層運限:大限宮干、流年(太歲宮宮干)、流月(斗君)、流日(初一進一格,p41)"""
    names = chart.natal_names
    ft = flying_table(sc)
    ming = names.index("命宮")
    dec = None
    for i, p in enumerate(chart.r.palaces):
        a, b = p.decadal.range
        if a <= xusui <= b:
            dec = i
    yi = R.bi(lunar_year_zhi)
    m_idx = (R.dou_jun_first_month(yi, ming) + eff_month - 1) % 12
    d_idx = (m_idx + lunar_day) % 12          # 初一 = 流月宮 + 1
    born_here = {}
    for k, s in enumerate(ft[year_gan]):
        j = chart.star_idx.get(s)
        if j is not None:
            born_here.setdefault(j, []).append(f"生年{s}{R.HUA[k]}")
    out = {}
    for tag, idx in (("大限", dec), ("流年", yi), ("流月", m_idx), ("流日", d_idx)):
        if idx is None:
            continue
        blk = year_palace_flight(chart, idx, sc, tag)
        blk["重疊生年四化"] = born_here.get(idx, ["無"])
        out[tag] = blk
    out["說明"] = ("欽天口徑:流年/流月/流日四化一律用所在宮之宮干(書頁87:『用乙天干針對流年者,是片面取義』);"
                 "流月以斗君起正月;流日初一自流月宮進一格(書頁41)。")
    return out
