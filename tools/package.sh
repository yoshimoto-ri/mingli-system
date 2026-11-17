#!/usr/bin/env bash
# 打包 skill 成 zip(Chromebook / Mac 用)
# 用法:  ./tools/package.sh                 打包全部 skill
#        ./tools/package.sh ziwei mingli-master   只打包指定的
# 產出在 dist/,每個 skill 一個 zip(claude.ai 不接受多資料夾 zip)
# config.json(存檔網址)只存在本機、不進 GitHub;打包時若有就自動帶入。
# mingli-master 缺 config.json 時跳過不打包,避免上傳後存檔功能失效。
set -euo pipefail
cd "$(dirname "$0")/.."
command -v zip >/dev/null || { echo "缺少 zip:Chromebook 請先執行 sudo apt install -y zip"; exit 1; }
mkdir -p dist
if [ $# -gt 0 ]; then skills=("$@"); else skills=($(ls skills)); fi
for s in "${skills[@]}"; do
  [ -f "skills/$s/SKILL.md" ] || { echo "略過 $s(找不到 SKILL.md)"; continue; }
  if [ "$s" = "mingli-master" ] && [ ! -f "skills/$s/config.json" ]; then
    echo "⚠ 略過 mingli-master:skills/mingli-master/config.json 不存在,打包後存檔網址會遺失"
    echo "  請在有 config.json 的電腦(Chromebook / Mac)打包,或先建立 config.json"
    continue
  fi
  rm -f "dist/$s.zip"
  (cd skills && zip -qr "../dist/$s.zip" "$s" -x "*/__pycache__/*" "*/.hko_cache/*" "*.pyc")
  extra=""; [ -f "skills/$s/config.json" ] && extra="(含 config.json)"
  echo "✓ dist/$s.zip $extra"
done
