---
name: name-numerology
description: 姓名學分析,東方含五格剖象數理派(康熙筆畫81數理、三才五行)與易經派姓名卦,西方含畢達哥拉斯數字學與生命靈數(表達數/靈魂渴望數/人格數/生日數)。使用者詢問名字好壞、改名、命名、嬰兒取名、英文名、生命靈數時必須使用本skill。計算一律執行script,康熙筆畫不可憑印象,須先查證。
---

# 姓名學 (name-numerology)

## 流程

### 1. 確認康熙筆畫(東方姓名學的成敗關鍵)
- 每個字的**康熙字典筆畫**必須先查證(web search「某字 康熙筆畫」),不可憑印象
- 特殊部首規則見 `references/strokes-rules.md`(氵=4、阝左=8、王=5、數字一~十按數值…)
- 向使用者覆述「字:筆畫」確認後再計算

### 2. 計算(必跑 script)
```bash
# 東方(複姓給兩數: --surname-strokes 8,7)
python3 scripts/numerology.py --east --surname-strokes 7 --given-strokes 3,8
# 西方: 支援英/法/德/拉丁文。變音符號自動還原(é→E、ü→U、ß→SS、œ→OE)
# Y前後無母音時作母音計;古典拉丁文 V/U、I/J 依使用者提供之拼寫計算,可先確認慣用寫法
# 中文名請使用者提供慣用英文名或護照拼音
python3 scripts/numerology.py --west --latin-name "John Smith" --birthdate 1990-08-15
# 可同時給兩組一次算完
```

### 3. 解讀
- 數字與五格意義 → `references/meanings.md`
- 順序:人格(主運)→ 三才配置 → 總格(後運)→ 地格外格 → 易經姓名卦 → 西方靈數對照
- 更名建議:結合五行喜用神(可調 wuxing skill 之八字分析),補不足之五行於三才與人格
- 結論遵守:論生不論死、論命不斷命;姓名為輔助,不誇大改名效果
