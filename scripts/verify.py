#!/usr/bin/env python3
"""Verify Job Hyogo pipeline output — coverage, categories, sources, and forbidden keywords."""
import json
import os
import sys

MARKER = "reports/.latest_json.txt"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
marker_path = os.path.join(BASE_DIR, MARKER)

with open(marker_path) as f:
    json_path = f.read().strip()
json_path = os.path.join(BASE_DIR, json_path) if not os.path.isabs(json_path) else json_path

with open(json_path, encoding="utf-8") as f:
    data = json.load(f)

errors = []
warnings = []

s = data["summary"]
print("=" * 60)
print("VERIFICATION REPORT")
print("=" * 60)

# ── 1. Basic counts ──────────────────────────────────────────────
print(f"\n📊 MAIN METRICS")
print(f"   Total matched:       {s['total_matched']}")
print(f"   Engineer:            {s['engineer_jobs']}")
print(f"   Factory/Warehouse:   {s['factory_warehouse_jobs']}")
print(f"   Large Factory:       {s['large_factory_jobs']}")
print(f"   Facebook:            {s['facebook_kept']}")
print(f"   Rejected total:      {s['rejected_total']}")
print(f"   Removed generic:     {s.get('removed_generic', '?')}")

if s["total_matched"] < 20:
    errors.append(f"Low job count: {s['total_matched']} (expected >= 20)")

# ── 2. Forbidden keyword audit in kept sections ────────────────
print(f"\n🔍 FORBIDDEN KEYWORD AUDIT")
forbidden_jp = ["事務", "通訳", "翻訳", "飲食", "レストラン", "販売", "接客", "ホテル", "コールセンター"]
forbidden_vn = ["phiên dịch", "bán hàng", "nhà hàng", "khách sạn"]
all_sections = {
    "top_jobs": data.get("top_jobs", []),
    "priority_jobs": data.get("priority_jobs", []),
    "engineer_jobs": data.get("engineer_jobs", []),
    "factory_warehouse_jobs": data.get("factory_warehouse_jobs", []),
    "large_factory_jobs": data.get("large_factory_jobs", []),
}

found_forbidden = 0
for sec_name, sec_jobs in all_sections.items():
    for job in sec_jobs:
        title = job.get("title", "")
        for kw in forbidden_jp:
            if kw in title:
                print(f"   ⚠ [{sec_name}] Forbidden JP '{kw}' in: {title[:60]}")
                found_forbidden += 1
                break

if found_forbidden == 0:
    print(f"   ✅ No forbidden JP keywords found in any kept section")
else:
    errors.append(f"Found {found_forbidden} forbidden JP keywords in kept sections")

# ── 3. Rejected categories ─────────────────────────────────────
print(f"\n🗑️ REJECTED CATEGORIES")
rejected = data.get("rejected", {})
for k, v in sorted(rejected.items()):
    print(f"   {k}: {v}")

if "tokutei" not in rejected:
    warnings.append("No tokutei rejections — may indicate filter gap")
if "interpreter_translation" not in rejected:
    warnings.append("No interpreter translation rejections")
if "office" not in rejected:
    warnings.append("No office rejections")

# ── 4. Description coverage in category sections ──────────────
print(f"\n📝 DESCRIPTION COVERAGE (category sections)")
for sec_name, sec_jobs in all_sections.items():
    total = len(sec_jobs)
    with_desc = sum(1 for j in sec_jobs if j.get("why_notable", "").strip())
    generic = sum(1 for j in sec_jobs if j.get("why_notable", "").strip().startswith("Cần tuyển"))
    pct = (with_desc / total * 100) if total > 0 else 0
    print(f"   {sec_name}: {with_desc}/{total} with desc ({pct:.0f}%) [{generic} generic]")
    if total > 0 and pct < 80:
        errors.append(f"{sec_name}: only {pct:.0f}% description coverage")

# ── 5. Source distribution ─────────────────────────────────────
print(f"\n📡 SOURCE DISTRIBUTION")
sources = {}
for job in data.get("all_jobs", []):
    src = job.get("source_name", "unknown")
    sources[src] = sources.get(src, 0) + 1
for src, count in sorted(sources.items()):
    print(f"   {src}: {count}")
if "Facebook" not in sources or sources.get("Facebook", 0) == 0:
    print(f"   ℹ️ Facebook: 0 (expected — static fallback only)")

# ── 6. Missing fields audit ────────────────────────────────────
print(f"\n⚠️ MISSING FIELDS")
all_jobs = data.get("all_jobs", [])
no_url = sum(1 for j in all_jobs if not j.get("source_url"))
no_salary = sum(1 for j in all_jobs if not j.get("salary"))
no_company = sum(1 for j in all_jobs if not j.get("company"))
no_area = sum(1 for j in all_jobs if not j.get("area"))
print(f"   Missing source_url: {no_url}/{len(all_jobs)} ({no_url/len(all_jobs)*100:.0f}%)")
print(f"   Missing salary:     {no_salary}/{len(all_jobs)} ({no_salary/len(all_jobs)*100:.0f}%)")
print(f"   Missing company:    {no_company}/{len(all_jobs)} ({no_company/len(all_jobs)*100:.0f}%)")
print(f"   Missing area:       {no_area}/{len(all_jobs)} ({no_area/len(all_jobs)*100:.0f}%)")

if no_url > len(all_jobs) * 0.5:
    warnings.append(f"High rate of missing source_url: {no_url}/{len(all_jobs)}")

# ── 7. HTML file check ──────────────────────────────────────────
html_path = json_path.replace(".json", ".html")
html_exists = os.path.exists(html_path)
print(f"\n📄 HTML FILE: {'✅ Found' if html_exists else '❌ MISSING'}: {html_path}")
if not html_exists:
    errors.append("HTML file not found")

# ── 8. Public server check (filesystem) ─────────────────────────
cron_file = f"/home/ubuntu/.hermes/cron/job_hyogo_report_2026-06-27_08-21.html"
cron_exists = os.path.exists(cron_file)
print(f"🌐 PUBLIC SERVER FILE: {'✅ Found' if cron_exists else '❌ MISSING'}: {cron_file}")
if not cron_exists:
    errors.append("Public server file not found")

# ── 9. Telegram summary check ──────────────────────────────────
tg_path = os.path.join(BASE_DIR, "reports/telegram_summary.md")
tg_exists = os.path.exists(tg_path)
print(f"📱 TELEGRAM SUMMARY: {'✅ Found' if tg_exists else '❌ MISSING'}: {tg_path}")
if not tg_exists:
    errors.append("Telegram summary not found")

# ── 10. Title_vi coverage ──────────────────────────────────────
tv_count = sum(1 for j in all_jobs if j.get("title_vi", "").strip())
print(f"\n🌐 TITLE VI COVERAGE: {tv_count}/{len(all_jobs)} ({tv_count/len(all_jobs)*100:.0f}%)")

# ── Summary ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
if errors:
    print(f"❌ ERRORS ({len(errors)}):")
    for e in errors:
        print(f"   • {e}")
else:
    print("✅ NO ERRORS")

if warnings:
    print(f"⚠️  WARNINGS ({len(warnings)}):")
    for w in warnings:
        print(f"   • {w}")
else:
    print("ℹ️  No warnings")

all_ok = len(errors) == 0
sys.exit(0 if all_ok else 1)
