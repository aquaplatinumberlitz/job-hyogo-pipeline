#!/usr/bin/env python3
"""Agent review for Job Hyogo pipeline – Passes 1-4.

Reads latest JSON from reports/.latest_json.txt, translates titles (JP→VN),
improves why_notable descriptions, propagates to category sections, writes back.
"""

import json
import os
import re

# ── paths ──────────────────────────────────────────────────────────────
MARKER = "reports/.latest_json.txt"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
marker_path = os.path.join(BASE_DIR, MARKER)

with open(marker_path) as f:
    json_path = f.read().strip()

json_path = os.path.join(BASE_DIR, json_path) if not os.path.isabs(json_path) else json_path
print(f"Reading: {json_path}")

with open(json_path, encoding="utf-8") as f:
    data = json.load(f)

jobs = data.get("all_jobs", [])
print(f"Total jobs in all_jobs: {len(jobs)}")

# ── Translation map (Japanese keyword → Vietnamese) ──────────────────
# Ordered by specificity (more specific first)
TRANS_MAP = [
    # Forklift / reach lift
    ("リーチリフト", "Lái xe nâng dạng vươn tới (Reach lift)"),
    ("リーチフォークリフト", "Lái xe nâng Reach"),
    ("フォークリフト", "Lái xe nâng"),
    # Welding
    ("溶接", "Thợ hàn"),
    # Crane
    ("クレーン", "Thợ vận hành cần cẩu"),
    ("玉掛", "Thợ móc cáp (玉掛)"),
    # NC / machining
    ("NC旋盤", "Thợ tiện NC"),
    ("マシニングセンタ", "Vận hành trung tâm gia công CNC"),
    # Coating / painting
    ("塗装", "Thợ sơn"),
    # Maintenance
    ("電気保全", "Nhân viên bảo trì điện"),
    ("機械保全", "Nhân viên bảo trì máy móc"),
    ("メンテナンス", "Nhân viên bảo trì thiết bị"),
    ("保全", "Nhân viên bảo trì"),
    ("保守", "Nhân viên bảo trì"),
    # Inspection / quality
    ("品質管理", "Nhân viên quản lý chất lượng"),
    ("品質保証", "Nhân viên đảm bảo chất lượng"),
    ("検品", "Nhân viên kiểm tra chất lượng"),
    ("外観検査", "Nhân viên kiểm tra ngoại quan"),
    ("検査", "Nhân viên kiểm tra chất lượng"),
    # Assembly
    ("組立", "Công nhân lắp ráp"),
    ("組み立て", "Công nhân lắp ráp"),
    ("取付", "Công nhân lắp đặt"),
    # Production / operator
    ("生産技術", "Kỹ thuật sản xuất"),
    ("オペレーター", "Nhân viên vận hành máy"),
    ("製造オペレーター", "Nhân viên vận hành máy sản xuất"),
    ("機械オペレーター", "Nhân viên vận hành máy"),
    ("製造", "Nhân viên sản xuất"),
    # Processing / machining
    ("加工", "Công nhân gia công"),
    ("機械加工", "Công nhân gia công cơ khí"),
    ("鋳造", "Công nhân đúc khuôn"),
    ("バリ取り", "Công nhân xử lý ba-vi"),
    ("成形", "Công nhân ép khuôn"),
    # Warehouse / logistics
    ("ピッキング", "Nhân viên nhặt hàng (Picking)"),
    ("入出庫", "Nhân viên xuất nhập kho"),
    ("入出荷", "Nhân viên xuất nhập kho"),
    ("倉庫", "Nhân viên kho"),
    ("物流", "Nhân viên logistics"),
    ("運搬", "Nhân viên vận chuyển"),
    # Packing
    ("包装", "Nhân viên đóng gói"),
    ("梱包", "Nhân viên đóng gói"),
    # Selection / sorting
    ("選別", "Nhân viên phân loại"),
    # Delivery
    ("配達", "Nhân viên giao hàng"),
    ("配送", "Nhân viên giao hàng"),
    # Electrical / electronic
    ("電気", "Nhân viên điện"),
    ("電子", "Nhân viên điện tử"),
    ("電気回路", "Kỹ thuật mạch điện"),
    # Design / CAD
    ("CAD", "Thiết kế CAD"),
    ("設計", "Thiết kế kỹ thuật"),
    # Engineer / analysis
    ("解析", "Kỹ sư phân tích"),
    ("エンジニア", "Kỹ sư"),
    ("設計技術者", "Kỹ sư thiết kế"),
    ("設計補助", "Trợ lý thiết kế"),
    # Equipment / facility
    ("設備", "Kỹ thuật thiết bị"),
    # Analysis / measurement
    ("分析", "Nhân viên phân tích"),
    ("計測", "Nhân viên đo lường"),
    # Shipping
    ("出荷", "Nhân viên xuất hàng"),
    # Coal / coke
    ("石炭", "Nhân viên sản xuất than"),
    ("コークス", "Nhân viên sản xuất than cốc"),
    # Monitoring / control
    ("監視", "Nhân viên giám sát"),
    ("操業", "Nhân viên vận hành sản xuất"),
    ("制御", "Kỹ thuật điều khiển"),
    # Food production
    ("食品製造", "Công nhân sản xuất thực phẩm"),
    ("チーズ", "Công nhân sản xuất phô mai"),
    ("マーガリン", "Công nhân sản xuất bơ thực vật"),
    # Convenience store
    ("コンビニ", "Nhân viên cửa hàng tiện lợi"),
    # Housework
    ("家事", "Nhân viên giúp việc gia đình"),
    ("使用人", "Người giúp việc"),
    # Light work / general
    ("軽作業", "Nhân viên nhẹ nhàng (Light work)"),
    # Installation
    ("取付", "Công nhân lắp đặt"),
    # Dissassembly
    ("解体", "Công nhân tháo dỡ"),
    # Steel / iron
    ("製鉄", "Nhân viên sản xuất thép"),
    ("製鋼", "Nhân viên luyện thép"),
    # Dock / ship
    ("船用", "Công nhân chế tạo tàu"),
]

def translate_title(title):
    """Translate Japanese job title to Vietnamese."""
    if not title:
        return ""
    
    # Handle short/noisy titles
    title_stripped = re.sub(r'[【〔《［\(\[]\s*[^】〕》］\)\]]+[】〕》］\)\]]', '', title).strip()
    title_stripped = re.sub(r'（[^）]*）', '', title_stripped).strip()
    title_stripped = re.sub(r'〈[^〉]*〉', '', title_stripped).strip()
    title_stripped = re.sub(r'[＜<][^＞>]*[＞>]', '', title_stripped).strip()
    title_stripped = re.sub(r'\s+', '', title_stripped)
    
    # First try matching full title (preferred - more accurate for description selection)
    # Then try the stripped version
    for kw, vn in TRANS_MAP:
        if kw in title:
            return vn
    
    # Try stripped version
    for kw, vn in TRANS_MAP:
        if kw in title_stripped:
            return vn
    
    # Fallback patterns for titles that don't match keyword table
    # Check for factory/production related
    if any(w in title for w in ['工場', '生産', '製造']):
        return "Nhân viên sản xuất"
    
    # Very short titles - check company field
    return "Nhân viên sản xuất"


def improve_description(job):
    """Improve why_notable description for a job."""
    title = job.get("title", "")
    title_vi = job.get("title_vi", "")
    desc = job.get("why_notable", "")
    company = job.get("company", "")
    area = job.get("area", "")
    salary = job.get("salary", "")
    source = job.get("source_name", "")
    
    # Skip if already has good description (not generic)
    if desc and not desc.startswith("Cần tuyển"):
        return desc
    
    # Match from Japanese title (avoids substring false positives in Vietnamese)
    jp = title
    
    # Forklift
    if "フォークリフト" in jp or "リーチリフト" in jp or "リーチフォークリフト" in jp:
        base = "Cần tuyển lái xe nâng vận chuyển hàng hóa trong kho, nhà xưởng."
    # Welding
    elif "溶接" in jp:
        base = "Cần tuyển thợ hàn, gia công kim loại cho các chi tiết máy móc, thiết bị."
    # Crane
    elif "クレーン" in jp or "玉掛" in jp:
        base = "Cần tuyển nhân viên vận hành cần cẩu, móc cáp nâng chuyển hàng hóa, vật liệu."
    # Maintenance
    elif any(kw in jp for kw in ["メンテナンス", "保全", "保守", "設備の保守", "設備"]):
        base = "Cần tuyển nhân viên bảo trì, bảo dưỡng thiết bị máy móc trong nhà máy."
    # Assembly
    elif "組立" in jp or "組み立て" in jp:
        base = "Cần tuyển công nhân lắp ráp linh kiện, sản phẩm trong nhà máy."
    # Production operator / machine operator
    elif "オペレーター" in jp:
        if "タイヤ" in jp:
            base = "Cần tuyển nhân viên vận hành máy sản xuất lốp xe, làm việc trong nhà máy sản xuất lốp ô tô."
        elif "樹脂" in jp or "プラスチック" in jp:
            base = "Cần tuyển nhân viên vận hành máy sản xuất linh kiện nhựa, gia công sản phẩm nhựa."
        elif "ゴム" in jp:
            base = "Cần tuyển nhân viên vận hành máy sản xuất linh kiện cao su, chi tiết cao su kỹ thuật."
        else:
            base = "Cần tuyển nhân viên vận hành máy móc, thiết bị sản xuất linh kiện công nghiệp."
    # Inspection / quality
    elif any(kw in jp for kw in ["検査", "検品", "品質管理", "品質保証", "外観検査"]):
        if "電子" in jp:
            base = "Cần tuyển nhân viên kiểm tra chất lượng linh kiện điện tử, kiểm tra vi mạch, bo mạch."
        elif "樹脂" in jp:
            base = "Cần tuyển nhân viên kiểm tra, phân loại sản phẩm nhựa, phát hiện lỗi sản phẩm."
        else:
            base = "Cần tuyển nhân viên kiểm tra chất lượng sản phẩm, phát hiện lỗi, đảm bảo tiêu chuẩn xuất xưởng."
    # Processing
    elif any(kw in jp for kw in ["加工", "機械加工"]):
        if "航空" in jp or "エンジン" in jp:
            base = "Cần tuyển công nhân gia công, chế tạo linh kiện động cơ máy bay, yêu cầu độ chính xác cao."
        elif "断熱材" in jp:
            base = "Cần tuyển công nhân gia công vật liệu cách nhiệt, cắt, tạo hình sản phẩm cách nhiệt."
        elif "石炭" in jp:
            base = "Cần tuyển công nhân gia công, xử lý than đá, vận hành thiết bị chế biến than."
        elif "金属" in jp:
            base = "Cần tuyển công nhân gia công kim loại, cắt, mài, đánh bóng chi tiết kim loại."
        elif "建機" in jp or "パワーショベル" in jp or "ショベル" in jp:
            base = "Cần tuyển công nhân gia công, chế tạo linh kiện máy xây dựng (máy xúc, máy ủi)."
        else:
            base = "Cần tuyển công nhân gia công, chế biến sản phẩm trong nhà máy."
    # Painting
    elif "塗装" in jp:
        base = "Cần tuyển thợ sơn, phun sơn các chi tiết, linh kiện sản phẩm công nghiệp."
    # Casting / die-cast
    elif any(kw in jp for kw in ["鋳造", "金型"]):
        base = "Cần tuyển công nhân đúc khuôn kim loại, xử lý ba-vi, đánh bóng sản phẩm đúc."
    # Warehouse / picking
    elif any(kw in jp for kw in ["ピッキング", "倉庫", "物流", "入出庫", "入出荷"]):
        if "フォークリフト" in jp or "リフト" in jp:
            base = "Cần tuyển nhân viên kho vận hành xe nâng, xuất nhập hàng hóa, sắp xếp kho."
        else:
            base = "Cần tuyển nhân viên kho, nhặt hàng, đóng gói, sắp xếp hàng hóa trong kho."
    # Packing
    elif "包装" in jp or "梱包" in jp:
        base = "Cần tuyển nhân viên đóng gói, bao bì sản phẩm hoàn thiện trước khi xuất hàng."
    # Picking
    elif "ピッキング" in jp:
        base = "Cần tuyển nhân viên nhặt hàng (picking) theo đơn hàng trong kho."
    # Design / CAD
    elif any(kw in jp for kw in ["CAD", "設計", "設計補助"]):
        base = "Cần tuyển kỹ sư thiết kế, vẽ CAD cho linh kiện cơ khí, thiết bị công nghiệp."
    # Analysis / engineer
    elif "解析" in jp or "エンジニア" in jp:
        base = "Cần tuyển kỹ sư phân tích, tính toán kết cấu, mô phỏng kỹ thuật."
    # Electrical / electronic
    elif any(kw in jp for kw in ["電気", "電子"]):
        base = "Cần tuyển nhân viên kỹ thuật điện/điện tử, lắp ráp, kiểm tra mạch điện."
    # Food production
    elif "食品" in jp or "チーズ" in jp or "マーガリン" in jp:
        if "チーズ" in jp:
            base = "Cần tuyển công nhân sản xuất, đóng gói phô mai trong nhà máy thực phẩm."
        elif "マーガリン" in jp:
            base = "Cần tuyển công nhân sản xuất bơ thực vật trong nhà máy thực phẩm."
        else:
            base = "Cần tuyển công nhân sản xuất, chế biến thực phẩm trong nhà máy."
    # Convenience store
    elif "コンビニ" in jp:
        base = "Cần tuyển nhân viên cửa hàng tiện lợi, phục vụ khách hàng, xếp hàng lên kệ."
    # Housework
    elif "家事" in jp or "使用人" in jp:
        base = "Cần tuyển nhân viên giúp việc nhà, dọn dẹp vệ sinh gia đình."
    # Coal / coke
    elif "石炭" in jp or "コークス" in jp:
        base = "Cần tuyển nhân viên vận hành sản xuất than, phân tích, xử lý số liệu sản xuất than cốc."
    # Light work / steel / general
    elif "軽作業" in jp:
        base = "Cần tuyển nhân viên làm việc nhẹ nhàng, đơn giản không yêu cầu kinh nghiệm."
    elif "製鉄" in jp or "製鋼" in jp:
        base = "Cần tuyển nhân viên bảo trì, kiểm tra thiết bị trong nhà máy luyện thép."
    elif "船用" in jp:
        base = "Cần tuyển công nhân gia công, chế tạo linh kiện động cơ tàu biển."
    # General factory
    elif any(w in jp for w in ['工場', '製造', '生産']):
        base = "Cần tuyển công nhân sản xuất, làm việc trong nhà máy, dây chuyền sản xuất."
    else:
        # Default: use existing or generic
        return desc  # Keep existing if not matched
    
    # Add salary if available
    if salary and salary not in base:
        base = base.rstrip('.')
        base += f". Lương: {salary}"
    
    return base


# ═════════════════════════════════════════════════════════════════════
# PASS 1: Translate titles
# ═════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("PASS 1: Title translation (JP→VN)")
print("=" * 60)

for i, job in enumerate(jobs):
    old_tv = job.get("title_vi", "")
    title = job.get("title", "")
    
    # Skip if already has a good translation
    if old_tv and len(old_tv) > 3 and not any(kw in title for kw in ['20', '40代', '月収', 'No.HJ']):
        continue
    
    new_tv = translate_title(title)
    if new_tv != old_tv:
        job["title_vi"] = new_tv
        print(f"[{i}] {title[:50]}...")
        print(f"    VN: {new_tv}")

# ═════════════════════════════════════════════════════════════════════
# PASS 2: Improve why_notable descriptions
# ═════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("PASS 2: Improve why_notable descriptions")
print("=" * 60)

improved_count = 0
for i, job in enumerate(jobs):
    old_desc = job.get("why_notable", "")
    new_desc = improve_description(job)
    
    if new_desc != old_desc:
        job["why_notable"] = new_desc
        improved_count += 1
        title = job.get("title", "")
        print(f"[{i}] {title[:50]}...")
        print(f"    OLD: {old_desc[:80]}")
        print(f"    NEW: {new_desc[:80]}")

print(f"\nImproved {improved_count} descriptions")

# ═════════════════════════════════════════════════════════════════════
# PASS 3: Fix mismatches — scan for cross-contamination
# ═════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("PASS 3: Scan for false positive mismatches")
print("=" * 60)

issue_count = 0
for i, job in enumerate(jobs):
    title = job.get("title", "")
    desc = job.get("why_notable", "")
    title_vi = job.get("title_vi", "")
    
    # Check for welding description on non-welding jobs
    if "thợ hàn" in desc.lower() and "溶接" not in title:
        if "hàn" in title_vi.lower() and not title_vi.lower().startswith("thợ hàn"):
            # Check this isn't actually welding
            is_non_welding = True
            for kw in ["SHOVEL", "建機", "パワーショベル", "機械加工", "加工"]:
                if kw.lower() in title.lower():
                    is_non_welding = True
                    break
            if is_non_welding and "溶接" not in title:
                print(f"[{i}] WELDING FALSE POSITIVE: desc={desc[:60]}")
                print(f"    title={title[:60]}")
                issue_count += 1
    
    # Check for "lái xe nâng" on non-forklift jobs
    if "lái xe nâng" in desc.lower() and not any(k in title for k in ["フォークリフト", "リーチ", "リフト"]):
        print(f"[{i}] FORKLIFT FALSE POSITIVE: desc={desc[:60]}")
        print(f"    title={title[:60]}")
        issue_count += 1

if issue_count == 0:
    print("No false positives detected.")
else:
    print(f"⚠ Found {issue_count} potential mismatches (reported above)")

# ═════════════════════════════════════════════════════════════════════
# PASS 4: Propagate why_notable to category sections
# ═════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("PASS 4: Propagate why_notable to category sections")
print("=" * 60)

notable_map = {j["id"]: j.get("why_notable", "") for j in jobs}
propagated = 0
for section_key in ["top_jobs", "priority_jobs", "engineer_jobs", "factory_warehouse_jobs", "large_factory_jobs"]:
    section_jobs = data.get(section_key, [])
    for job in section_jobs:
        if job["id"] in notable_map and notable_map[job["id"]]:
            if job.get("why_notable") != notable_map[job["id"]]:
                job["why_notable"] = notable_map[job["id"]]
                propagated += 1

print(f"Propagated {propagated} why_notable entries to category sections")

# Also propagate title_vi to category sections (belt and suspenders)
tv_map = {j["id"]: j.get("title_vi", "") for j in jobs}
tv_propagated = 0
for section_key in ["top_jobs", "priority_jobs", "engineer_jobs", "factory_warehouse_jobs", "large_factory_jobs"]:
    section_jobs = data.get(section_key, [])
    for job in section_jobs:
        if job["id"] in tv_map and tv_map[job["id"]]:
            if job.get("title_vi") != tv_map[job["id"]]:
                job["title_vi"] = tv_map[job["id"]]
                tv_propagated += 1

print(f"Propagated {tv_propagated} title_vi entries to category sections")

# ═════════════════════════════════════════════════════════════════════
# Write back
# ═════════════════════════════════════════════════════════════════════
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

total_size = os.path.getsize(json_path)
print(f"\n✅ Written: {json_path} ({total_size} bytes)")

# Final summary
translated = sum(1 for j in jobs if j.get("title_vi", "").strip())
notable_nonempty = sum(1 for j in jobs if j.get("why_notable", "").strip())
notable_improved = sum(1 for j in jobs if j.get("why_notable", "").strip() and not j.get("why_notable", "").startswith("Cần tuyển"))
print(f"Titles translated: {translated}/{len(jobs)}")
print(f"Descriptions non-empty: {notable_nonempty}/{len(jobs)}")
print(f"Descriptions improved (non-generic): {notable_improved}/{len(jobs)}")
