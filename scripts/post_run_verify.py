#!/usr/bin/env python3
"""Post-run verification of pipeline output."""
import json

with open("/home/ubuntu/job-hyogo-pipeline/reports/job_hyogo_report_2026-06-21_08-17-48.json") as f:
    data = json.load(f)

print("=== COVERAGE CHECK ===")
section_keys = ['top_jobs', 'priority_jobs', 'engineer_jobs',
                'factory_warehouse_jobs', 'large_factory_jobs']
all_ok = True
for sk in section_keys:
    if sk in data:
        jobs = data[sk]
        tvi = sum(1 for j in jobs if j.get('title_vi'))
        wn = sum(1 for j in jobs if j.get('why_notable'))
        ok = tvi == len(jobs) and wn == len(jobs)
        status = "OK" if ok else "ISSUE"
        print(f"  {sk}: {len(jobs)} jobs, title_vi={tvi}/{len(jobs)}, why_notable={wn}/{len(jobs)} [{status}]")
        if not ok:
            all_ok = False

print()
print("=== REJECTED CATEGORIES ===")
for cat, count in sorted(data.get('rejected', {}).items()):
    if count > 0:
        print(f"  {cat}: {count}")

print()
print("=== FORBIDDEN KEYWORD AUDIT ===")
forbidden = ['\u4e8b\u52d9', '\u901a\u8a33', '\u7ffb\u8a33', '\u996e\u98df',
             '\u30ec\u30b9\u30c8\u30e9\u30f3', '\u8ca9\u58f2', '\u63a5\u5ba2',
             '\u30db\u30c6\u30eb', '\u30b3\u30fc\u30eb\u30bb\u30f3\u30bf\u30fc']
found_issues = False
for sk in section_keys:
    if sk in data:
        for job in data[sk]:
            t = job.get('title', '')
            for fw in forbidden:
                if fw in t:
                    print(f"  WARNING [{fw}] in {sk}: {job['id'][:8]} \"{t[:60]}\"")
                    found_issues = True
if not found_issues:
    print("  No forbidden keywords found in kept sections.")

print()
print("=== SOURCE DISTRIBUTION ===")
src_stats = data.get('source_stats', {})
for src, count in sorted(src_stats.items()):
    print(f"  {src}: {count}")

print()
print("=== MISSING FIELDS ===")
no_url = sum(1 for j in data['all_jobs'] if not j.get('source_url'))
no_salary = sum(1 for j in data['all_jobs'] if not j.get('salary'))
no_company = sum(1 for j in data['all_jobs'] if not j.get('company'))
total = len(data['all_jobs'])
print(f"  Missing source_url: {no_url}/{total} ({no_url/total*100:.0f}%)")
print(f"  Missing salary: {no_salary}/{total} ({no_salary/total*100:.0f}%)")
print(f"  Missing company: {no_company}/{total} ({no_company/total*100:.0f}%)")
if no_url > total * 0.5:
    print("  NOTE: >50% missing source_url")

print()
if all_ok and not found_issues:
    print("OVERALL: ALL CHECKS PASSED")
else:
    print("OVERALL: ISSUES FOUND - check above")
