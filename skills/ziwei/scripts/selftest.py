#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回歸測試:隨機出生資料 N 張盤,py-iztro 與獨立規則引擎必須全數一致;另測已知邊界案例。
python3 selftest.py [N]"""
import json, os, random, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
def run(date, g, extra=()):
    o = subprocess.run([sys.executable, os.path.join(HERE, "chart.py"), "--date", date, "--tz", "Asia/Taipei",
                        "--lon", "121.56", "--gender", g, *extra], capture_output=True, text=True)
    return json.loads(o.stdout)
fails = 0
cases = [  # (出生, 性別, 預期生年干支, 說明)
    ("2024-02-06 12:00", "男", "癸卯", "立春後、春節前:年干須依正月初一"),
    ("2025-08-15 10:00", "女", "乙巳", "閏六月後半:依七月安星"),
    ("1990-08-15 23:15", "女", "庚午", "晚子時換日"),
]
for d, g, gz, note in cases:
    r = run(d, g)
    ok = r["交叉驗證"]["結果"] == "通過" and r["交叉驗證"]["生年干支"] == gz
    fails += not ok
    print(("OK  " if ok else "FAIL"), note, r["交叉驗證"]["生年干支"], r["交叉驗證"]["差異"])
r = run("1963-08-15 22:30", "男", ("--target", "2028-01-06"))
ok = r["運限"]["流月"]["干支"] == "癸丑"
fails += not ok
print(("OK  " if ok else "FAIL"), "臘月小寒前流月干支須為癸丑:", r["運限"]["流月"]["干支"])
r = run("1963-08-15 22:30", "男", ("--flying",))
fl = r["欽天飛化層"]
ok = (fl["來因宮"] == "田宅(亥)" and "命宮(申) 離心自化科(太陰)" in fl["自化"]
      and "財帛(辰) 離心自化祿(天同)" in fl["自化"]
      and any(c.startswith("遷移(寅) → 夫妻(午)[沖官祿] → 命宮(申) → 財帛(辰)") for c in fl["忌轉忌"]["鏈"]))
fails += not ok
print(("OK  " if ok else "FAIL"), "欽天飛化層:來因宮、離心自化、忌轉忌三層", fl["來因宮"], fl["自化"])
N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
random.seed(7)
for _ in range(N):
    d = f"{random.randint(1930,2025)}-{random.randint(1,12):02d}-{random.randint(1,28):02d} {random.randint(0,23):02d}:{random.randint(0,59):02d}"
    r = run(d, random.choice("男女"))
    if r["交叉驗證"]["結果"] != "通過":
        fails += 1; print("FAIL", d, r["交叉驗證"]["差異"])
print(f"隨機 {N} 盤完成,失敗 {fails}")
sys.exit(1 if fails else 0)
