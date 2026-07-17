---
name: wuxing
description: 陰陽五行理論基礎引擎,含天干地支五行、地支藏干、八字五行分布統計、日主旺衰粗判、生剋乘侮關係查詢。當紫微、姓名學、農民曆、占星等skill需要五行生剋判斷、喜用神參考、健康五行對應、顏色方位數字開運建議時使用本skill;使用者問五行缺什麼、屬什麼五行、適合什麼顏色方位時亦必須使用。
---

# 陰陽五行 (wuxing)

## 計算(必跑 script)
```bash
python3 scripts/wuxing.py --bazi "庚午 甲申 癸丑 壬子"   # 四柱五行分布(四柱由 calendar-converter 取得)
python3 scripts/wuxing.py --query 庚                      # 單干支查五行/藏干
python3 scripts/wuxing.py --relation 金,木                # 生剋關係
```

## 解讀
理論細節讀 `references/wuxing-theory.md`(生剋乘侮、四時旺衰、臟腑/方位/顏色對應、喜用神原則)。
- 「旺衰粗判」僅為初步;喜用神給「參考方向」,不下絕對論斷
- 健康對應僅作保健提醒,一律建議就醫檢查為準
- 本skill為其他命理skill的共用底層:更名補五行、擇日配五行、開運色方位皆由此出
