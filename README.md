# 全面命理預測系統 (Mingli System)

一套給 [Claude](https://claude.ai) 使用的命理分析 Skill 系統，整合紫微斗數、西洋占星、易經卜卦、農民曆擇日、姓名學、八字五行等多套命理工具，以精確運算（Python + Swiss Ephemeris + lunar-python）搭配 LLM 的解讀能力，並可將分析結果自動存入你自己的 Google Sheets。

## 為什麼要把運算和解讀分開？

Claude 是語言模型，長於理解與敘述，但不擅長精確的曆法換算、天文星曆計算、六爻裝卦等機械性推導。這套系統的核心設計原則是：

> **Claude 負責理解需求與解讀輸出，Python script 負責精確運算。排盤一律執行 script，嚴禁心算。**

## 系統組成

| Skill | 功能 |
|---|---|
| `calendar-converter` | 真太陽時／日光節約時間／子時換日規則／農曆換算（核心時間基準） |
| `ziwei` | 紫微斗數排盤（三合派＋中州派），含本命十二宮、四化、大限、流年流月流日 |
| `western-astrology` | 西洋占星（古典占星／擇日占星／靈魂占星），Swiss Ephemeris 引擎 |
| `iching` | 易經卜卦（文王卦六爻納甲、梅花易數） |
| `tongshu` | 農民曆擇日（宜忌、沖煞、吉時、區間擇日掃描） |
| `name-numerology` | 姓名學（東方五格數理＋易經派姓名卦；西方畢氏數字學，支援英/法/德/拉丁文） |
| `bazi-reference` | 八字速查表（十神、日主強弱、用神喜忌、格局分析、大運流年、六十甲子） |
| `wuxing` | 陰陽五行底層引擎（生剋乘侮、八字五行分布、喜用神參考） |
| `mingli-master` | 主控流程：收集資料 → 調度各 skill → 綜合解讀 → 寫入 Google Sheets |

## 安裝方式

### claude.ai（網頁／App）

1. 每個 `skills/<name>/` 資料夾各自打包成 zip（資料夾名稱＝zip 檔名，內含一個 `SKILL.md`）
2. Settings → Customize → Skills → 上傳 zip

### Claude Code

```bash
git clone https://github.com/<你的帳號>/mingli-system.git
cp -r mingli-system/skills/* ~/.claude/skills/
pip install lunar-python py-iztro pyswisseph opencc-python-reimplemented reportlab
```

## 部署 Google Sheets 寫入端點（選用，但建議）

想要每次分析結果自動存檔，需要自己部署一個 Google Apps Script Web App（跑在你自己的 Google 帳號下，資料只存在你自己的 Drive，不會經過任何第三方）：

1. 開 [script.google.com](https://script.google.com) → 新增專案
2. 貼上 `mingli-master/assets/apps-script.gs` 全部內容 → 存檔
3. 部署 → 新增部署 → 類型選「網頁應用程式」
   - 執行身分：**我**
   - 存取權：**任何人**
4. 授權你的 Google 帳號 → 複製產生的 Web App 網址（`https://script.google.com/macros/s/.../exec`）
5. 複製 `config.example.json` 為 `config.json`，把網址填入 `webhook_url`：

```json
{
  "webhook_url": "https://script.google.com/macros/s/你的部署ID/exec"
}
```

`config.json` 已被 `.gitignore` 排除，不會被推上 GitHub，你的網址只存在本機。

執行後會自動在你的雲端硬碟建立「命理系統」資料夾，內含試算表逐筆記錄每次分析的姓名、生辰、問事類別與各系統摘要結論。

## 使用方式

在 claude.ai 對話中直接說「我要算命」或「幫我看紫微」，`mingli-master` 會自動接手：

1. 詢問你要用哪個系統（易經卜卦／紫微／占星／綜合分析）
2. 收集必要資料（性別、出生年月日時、出生地——缺一不可，尤其**性別**會影響紫微大限順逆行方向）
3. 調度對應 skill 運算並產出報告
4. 詢問是否需要輸出 PDF（可選）
5. 自動存入你的 Google Sheets（如已設定 Webhook）

## 準確度驗證

開發過程中已對每個 skill 做過交叉驗證：

- 紫微：與 py-iztro 官方範例逐項核對命主、五行局、大限
- 占星：J2000 太陽黃經誤差 <0.05°（與理論值比對）
- 易經：乾為天裝卦與教科書逐爻核對
- 農曆：閏月、真太陽時均時差誤差 <0.5 分鐘
- 姓名學：畢氏數字學手算交叉驗證

## 命理原則

本系統的所有解讀遵循兩條鐵律：

- **論生不論死**：不推斷死亡、壽限、絕症結局
- **論命不斷命**：不下宿命定論，給趨勢、給條件、給建議，選擇權在使用者

涉及健康問題一律提醒就醫；命理僅供參考，不作為重大財務、法律決策的唯一依據。

## License

MIT License，詳見 [LICENSE](LICENSE)。

## 致謝

參考了 [Wolke/bazi-mingli](https://github.com/Wolke/bazi-mingli) 的八字十神體系設計，以及 [FANzR-arch/Numerologist_skills](https://github.com/FANzR-arch/Numerologist_skills) 的資料收集追問邏輯。

## 三台電腦同步與打包(Chromebook / Mac / Windows)

GitHub 是唯一主版本。任何一台改完就 push,換到另一台先 pull 再動工。

| 動作 | Chromebook / Mac(終端機) | Windows(PowerShell) |
|---|---|---|
| 第一次下載 | `git clone https://github.com/yoshimoto-ri/mingli-system.git` | 同左,另執行 `git config core.autocrlf true` |
| 同步最新版 | `git pull` | `git pull` |
| 推上修改 | `git pull` → `git add -A` → `git commit -m "說明"` → `git push` | 同左 |
| 打包 skill | `./tools/package.sh`(或加 skill 名稱) | `.\tools\package.ps1`(或加 skill 名稱) |

- 打包結果在 `dist/`,每個 skill 一個 zip,用 claude.ai 的「取代」上傳。
- **`skills/mingli-master/config.json` 存放存檔網址,只放在 Chromebook / Mac 本機,不進 GitHub、不放 Windows。**
  打包腳本會自動帶入;缺少時會跳過 mingli-master,避免上傳後存檔功能失效。
