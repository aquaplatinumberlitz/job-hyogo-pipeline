#!/usr/bin/env python3
"""Fix specific translation/description mismatches found during agent review."""
import json
import os

MARKER = "reports/.latest_json.txt"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
marker_path = os.path.join(BASE_DIR, MARKER)

with open(marker_path) as f:
    json_path = f.read().strip()
json_path = os.path.join(BASE_DIR, json_path) if not os.path.isabs(json_path) else json_path

with open(json_path, encoding="utf-8") as f:
    data = json.load(f)

jobs = data.get("all_jobs", [])

# ── Fix SPECIFIC jobs by id ──────────────────────────────────────────
fixes = {
    # [9] 航空エンジン部品の加工・組立・検査 → primary is processing+assembly
    None: None,  # placeholder - will match by title heuristic
}

# Fix by title substring (more robust than index)
for job in jobs:
    t = job.get("title", "")
    
    # [9] Aircraft engine parts: processing, assembly, inspection
    if "航空エンジン部品の加工・組立・検査" in t:
        job["title_vi"] = "Công nhân gia công, lắp ráp, kiểm tra linh kiện động cơ máy bay"
        job["why_notable"] = "Cần tuyển công nhân gia công, lắp ráp, kiểm tra linh kiện động cơ máy bay, yêu cầu độ chính xác cao. Lương: 時給1,700～2,000円"
    
    # [13] 汎用ロボットの組立・検査 → primary is assembly
    elif "汎用ロボットの組立・検査" in t and "月収32万円" in t:
        job["title_vi"] = "Công nhân lắp ráp robot đa năng"
        job["why_notable"] = "Cần tuyển công nhân lắp ráp, kiểm tra robot đa năng trong nhà máy."
    
    # [18] 汎用ロボットの組立・検査 (duplicate)
    elif "汎用ロボットの組立・検査" in t and "月収32万円可" in t:
        job["title_vi"] = "Công nhân lắp ráp robot đa năng"
        job["why_notable"] = "Cần tuyển công nhân lắp ráp, kiểm tra robot đa năng trong nhà máy."
    
    # [28] 小型部品の組立・検査 → assembly primary
    elif "小型部品の組立・検査" in t:
        job["title_vi"] = "Công nhân lắp ráp, kiểm tra linh kiện nhỏ"
        job["why_notable"] = "Cần tuyển công nhân lắp ráp, kiểm tra linh kiện nhỏ trong nhà máy."
    
    # [33] 給湯器部品の製造OP・検査 → manufacturing operator primary
    elif "給湯器部品の製造OP・検査" in t:
        job["title_vi"] = "Nhân viên vận hành máy sản xuất linh kiện máy nước nóng"
        job["why_notable"] = "Cần tuyển nhân viên vận hành máy sản xuất, kiểm tra linh kiện máy nước nóng, không yêu cầu kinh nghiệm."
    
    # [39] 成形・検査・梱包作業 → molding primary
    elif "空港や物流で使う部品の成形・検査・梱包" in t:
        job["title_vi"] = "Công nhân ép khuôn, kiểm tra, đóng gói linh kiện sân bay"
        job["why_notable"] = "Cần tuyển công nhân ép khuôn, kiểm tra chất lượng, đóng gói linh kiện thiết bị sân bay và logistics."
    
    # [61] チーズの製造・梱包 → food production, not just packing
    elif "チーズの製造・梱包" in t:
        job["title_vi"] = "Công nhân sản xuất, đóng gói phô mai"
        job["why_notable"] = "Cần tuyển công nhân sản xuất, đóng gói phô mai trong nhà máy thực phẩm."

# ── Propagate fixes to category sections ────────────────────────────
notable_map = {j["id"]: j.get("why_notable", "") for j in jobs}
tv_map = {j["id"]: j.get("title_vi", "") for j in jobs}

for section_key in ["top_jobs", "priority_jobs", "engineer_jobs", "factory_warehouse_jobs", "large_factory_jobs"]:
    section_jobs = data.get(section_key, [])
    for job in section_jobs:
        if job["id"] in notable_map and notable_map[job["id"]]:
            job["why_notable"] = notable_map[job["id"]]
        if job["id"] in tv_map and tv_map[job["id"]]:
            job["title_vi"] = tv_map[job["id"]]

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✅ Fixes applied and written to: {json_path}")

# Verify specific jobs
for job in jobs:
    t = job.get("title", "")
    if any(k in t for k in ["航空エンジン", "汎用ロボット", "小型部品の組立", "給湯器", "空港や物流", "チーズの製造"]):
        print(f"  Fixed: {job['title_vi']} | {job.get('why_notable','')[:60]}")
