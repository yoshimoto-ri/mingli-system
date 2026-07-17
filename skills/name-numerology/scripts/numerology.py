#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
姓名學計算(東方五格/易經派 + 西方畢達哥拉斯)
東方: python3 numerology.py --east --surname-strokes 7 --given-strokes 3,8
  (筆畫一律用【康熙字典筆畫】,特殊部首規則見 references/strokes-rules.md;複姓給兩數如 8,7)
西方: python3 numerology.py --west --latin-name "John Smith" --birthdate 1990-08-15
可同時給兩組參數一次算完。輸出 JSON。
"""
import argparse, json, unicodedata

JIXIONG = {1:("吉","太極首領"),2:("凶","兩儀分離"),3:("吉","三才鼎立"),4:("凶","四象凶變"),5:("吉","五行俱權"),
6:("吉","六爻安穩"),7:("吉","剛毅果斷"),8:("吉","堅剛意志"),9:("凶","大成含悲"),10:("凶","萬事終局"),
11:("吉","旱苗逢雨"),12:("凶","掘井無泉"),13:("吉","春日牡丹"),14:("凶","破兆淚落"),15:("吉","福壽圓滿"),
16:("吉","厚重載德"),17:("吉","剛強突破"),18:("吉","鐵鏡重磨"),19:("凶","風雲蔽月"),20:("凶","非業破運"),
21:("吉","明月中天"),22:("凶","秋草逢霜"),23:("吉","旭日東昇"),24:("吉","掘藏得金"),25:("吉","英敏資性"),
26:("半吉半凶","變怪英雄"),27:("半吉半凶","增長慾望"),28:("凶","闊水浮萍"),29:("吉","智謀奏功"),30:("半吉半凶","浮沉不定"),
31:("吉","智勇得志"),32:("吉","寶馬金鞍"),33:("吉","旭日昇天"),34:("凶","破家災難"),35:("吉","高樓望月"),
36:("凶","波瀾重疊"),37:("吉","猛虎出林"),38:("半吉","磨鐵成針"),39:("吉","富貴榮華"),40:("半吉半凶","謹慎退安"),
41:("吉","德望高大"),42:("凶","博而不精"),43:("凶","外祥內苦"),44:("凶","愁眉難展"),45:("吉","順風揚帆"),
46:("凶","載寶沉舟"),47:("吉","點石成金"),48:("吉","古松立鶴"),49:("凶","吉凶難分"),50:("半吉半凶","一成一敗"),
51:("半吉半凶","盛衰交加"),52:("吉","先見之明"),53:("凶","外祥內患"),54:("凶","石上栽花"),55:("半吉半凶","外美內苦"),
56:("凶","浪裡行舟"),57:("吉","寒雪青松"),58:("半吉","先苦後甘"),59:("凶","意志薄弱"),60:("凶","搖動不安"),
61:("吉帶凶","名利防訌"),62:("凶","基礎虛弱"),63:("吉","舟歸平海"),64:("凶","浮沉破敗"),65:("吉","巨流歸海"),
66:("凶","進退維谷"),67:("吉","天賦通達"),68:("吉","發明有功"),69:("凶","窮迫非業"),70:("凶","殘菊逢霜"),
71:("吉帶凶","內心勞苦"),72:("半吉半凶","先甘後苦"),73:("半吉","志高平安"),74:("凶","殘花無實"),75:("半吉半凶","退守保吉"),
76:("凶","離散傾覆"),77:("半吉半凶","樂極生悲"),78:("半吉半凶","中年後凶"),79:("凶","精力不足"),80:("凶帶吉","隱遁得安"),
81:("吉","還元回春")}
WX_NUM = {1:"木",2:"木",3:"火",4:"火",5:"土",6:"土",7:"金",8:"金",9:"水",0:"水"}
SHENG = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
KE = {"木":"土","土":"水","水":"火","火":"金","金":"木"}
TRI = {1:"乾",2:"兌",3:"離",4:"震",5:"巽",6:"坎",7:"艮",8:"坤"}
TRIB = {"乾":(1,1,1),"兌":(1,1,0),"離":(1,0,1),"震":(1,0,0),"巽":(0,1,1),"坎":(0,1,0),"艮":(0,0,1),"坤":(0,0,0)}
BT = {v:k for k,v in TRIB.items()}
_rows={"乾":"乾為天 天澤履 天火同人 天雷无妄 天風姤 天水訟 天山遯 天地否","兌":"澤天夬 兌為澤 澤火革 澤雷隨 澤風大過 澤水困 澤山咸 澤地萃","離":"火天大有 火澤睽 離為火 火雷噬嗑 火風鼎 火水未濟 火山旅 火地晉","震":"雷天大壯 雷澤歸妹 雷火豐 震為雷 雷風恆 雷水解 雷山小過 雷地豫","巽":"風天小畜 風澤中孚 風火家人 風雷益 巽為風 風水渙 風山漸 風地觀","坎":"水天需 水澤節 水火既濟 水雷屯 水風井 坎為水 水山蹇 水地比","艮":"山天大畜 山澤損 山火賁 山雷頤 山風蠱 山水蒙 艮為山 山地剝","坤":"地天泰 地澤臨 地火明夷 地雷復 地風升 地水師 地山謙 坤為地"}
NAME={}
for up,row in _rows.items():
    for low,nm in zip(["乾","兌","離","震","巽","坎","艮","坤"],row.split()): NAME[(up,low)]=nm

PY = {c: (i % 9) + 1 for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}
VOWELS = set("AEIOU")

def latinize(name):
    """英/法/德/拉丁文正規化: 變音符號還原基字, 合字拆開"""
    s = name.upper().replace("ß", "SS").replace("Æ", "AE").replace("Œ", "OE").replace("Ø", "O").replace("Đ", "D").replace("Þ", "TH")
    s = unicodedata.normalize("NFD", s)
    return [c for c in s if c.isalpha() and c in PY]

def is_vowel(chars, i):
    """Y 規則: 前後皆非 AEIOU 時, Y 作母音計"""
    c = chars[i]
    if c in VOWELS: return True
    if c == "Y":
        prev_v = i > 0 and chars[i-1] in VOWELS
        next_v = i < len(chars)-1 and chars[i+1] in VOWELS
        return not (prev_v or next_v)
    return False

def reduce_n(n, masters=(11, 22, 33)):
    while n > 9 and n not in masters:
        n = sum(int(c) for c in str(n))
    return n

def grid(num):
    g = (num - 1) % 81 + 1
    jx, desc = JIXIONG[g]
    return {"數": num, "吉凶": jx, "斷語": desc, "五行": WX_NUM[num % 10]}

def sancai_judge(t, r, d):
    def rel(a, b):
        if a == b: return "比和(吉)"
        if SHENG[a] == b: return "生(吉)"
        if SHENG[b] == a: return "被生(吉)"
        if KE[a] == b: return "剋(凶)"
        return "被剋(凶)"
    return {"天→人": rel(t, r), "人→地": rel(r, d),
            "要旨": "三才相生比和為吉;人格受天地夾剋最忌,主基礎與境遇不安"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--east", action="store_true"); ap.add_argument("--west", action="store_true")
    ap.add_argument("--surname-strokes"); ap.add_argument("--given-strokes")
    ap.add_argument("--latin-name"); ap.add_argument("--birthdate")
    a = ap.parse_args()
    out = {}

    if a.east and a.surname_strokes and a.given_strokes:
        s = [int(x) for x in a.surname_strokes.split(",")]
        g = [int(x) for x in a.given_strokes.split(",")]
        tian = s[0] + 1 if len(s) == 1 else s[0] + s[1]
        ren = s[-1] + g[0]
        di = g[0] + 1 if len(g) == 1 else sum(g[:2])
        zong = sum(s) + sum(g)
        if len(s) == 1 and len(g) == 1: wai = 2
        elif len(s) == 1: wai = 1 + g[-1]
        else: wai = s[0] + (g[-1] if len(g) > 1 else 1)
        sc = {"天格": grid(tian), "人格": grid(ren), "地格": grid(di), "外格": grid(wai), "總格": grid(zong)}
        out["五格剖象"] = sc
        out["三才"] = {"配置": sc["天格"]["五行"] + sc["人格"]["五行"] + sc["地格"]["五行"],
                      **sancai_judge(sc["天格"]["五行"], sc["人格"]["五行"], sc["地格"]["五行"])}
        u, l, d = sum(s) % 8 or 8, sum(g) % 8 or 8, zong % 6 or 6
        bits = TRIB[TRI[l]] + TRIB[TRI[u]]
        vb = tuple(b ^ (1 if i + 1 == d else 0) for i, b in enumerate(bits))
        out["易經派姓名卦"] = {"起卦法": "姓筆畫為上卦、名筆畫為下卦(mod 8),總筆畫 mod 6 為動爻",
            "本卦": NAME[(BT[bits[3:]], BT[bits[:3]])], "動爻": f"第{d}爻",
            "變卦": NAME[(BT[vb[3:]], BT[vb[:3]])]}

    if a.west and a.latin_name:
        nm = latinize(a.latin_name)
        expr = reduce_n(sum(PY[c] for c in nm))
        soul = reduce_n(sum(PY[c] for i, c in enumerate(nm) if is_vowel(nm, i)))
        pers = reduce_n(sum(PY[c] for i, c in enumerate(nm) if not is_vowel(nm, i)))
        out["畢達哥拉斯"] = {"姓名": a.latin_name, "正規化": "".join(nm),
            "表達數Expression": expr, "靈魂渴望數SoulUrge": soul, "人格數Personality": pers}
        if a.birthdate:
            y, m, d = a.birthdate.split("-")
            lp = reduce_n(reduce_n(int(y)) + reduce_n(int(m)) + reduce_n(int(d)))
            bd = reduce_n(int(d))
            out["畢達哥拉斯"]["生命靈數LifePath"] = lp
            out["畢達哥拉斯"]["生日數Birthday"] = bd
            out["畢達哥拉斯"]["註"] = "生命靈數採年月日分別化約後加總法,11/22/33為卓越數不再化約"

    print(json.dumps(out or {"error": "請給 --east 或 --west 參數組"}, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
