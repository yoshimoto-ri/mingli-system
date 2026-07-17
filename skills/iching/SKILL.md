---
name: iching
description: 易經卜卦,含文王卦(六爻納甲、世應、六親、六獸、旬空)與梅花易數(時間/數字起卦、體用互變)。使用者問事占卜——尋物、合作吉凶、考運、感情走向、決策吉凶、是非官司、出行、任何「這件事會如何」的單一事件提問——或無出生時辰無法排紫微時,必須使用本skill起卦,嚴禁心算裝卦或自行編造卦象。
---

# 易經卜卦 (iching)

## 起卦(必跑 script)

問卦時刻一律用**使用者當地的當下時間**(系統當下),格式如下:

文王卦(預設程式擲錢;使用者自己搖過卦可用 --lines 輸入):
```bash
python3 scripts/divine.py --method liuyao --datetime "2026-06-11 21:30" --tz Asia/Taipei
python3 scripts/divine.py --method liuyao --datetime "..." --lines 788697   # 初→上;6老陰7少陽8少陰9老陽
```
梅花易數(預設年月日時起卦;使用者報數用 --numbers):
```bash
python3 scripts/divine.py --method meihua --datetime "2026-06-11 21:30" --tz Asia/Taipei
python3 scripts/divine.py --method meihua --datetime "..." --numbers "17,32"
```

## 選卦原則
- 具體事件吉凶、應期、涉及他人(官司/合作/感情對象) → 文王卦
- 快速問吉凶、靈感觸機、數字/字數起卦 → 梅花易數
- 同一事不重複起卦(「不誠不占、不疑不占、一事一占」)

## 解讀
讀 `references/interpretation.md`(用神對照、旺衰、動變、空亡、六獸、體用生剋)。
結論遵守:**論生不論死、論命不斷命**;給趨勢與條件,不下死語;健康問題提醒就醫。
