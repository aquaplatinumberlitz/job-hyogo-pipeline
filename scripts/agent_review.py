#!/usr/bin/env python3
"""
Agent review step for Job Hyogo pipeline — cron-mode safe.

Handles all 4 passes:
  1. Translate Japanese titles -> Vietnamese (title_vi)
  2. Improve why_notable descriptions
  3. Catch false-positive cross-contamination
  4. Propagate why_notable to category sections (Pass 4, critical!)

Usage (after --phase crawl):
  python3 /home/ubuntu/.hermes/skills/research/japan-job-search/scripts/agent_review.py
  # or drop into pipeline dir:
  cd /home/ubuntu/job-hyogo-pipeline && python3 /home/ubuntu/.hermes/skills/research/japan-job-search/scripts/agent_review.py
"""
import json, re, os

# ── 1. Locate JSON ───────────────────────────────────────────────────────
MARKER = "/home/ubuntu/job-hyogo-pipeline/reports/.latest_json.txt"
if not os.path.exists(MARKER):
    # Fallback: scan for most recent
    reports_dir = "/home/ubuntu/job-hyogo-pipeline/reports"
    files = [f for f in os.listdir(reports_dir) if f.startswith("job_hyogo_report_") and f.endswith(".json")]
    if not files:
        print("ERROR: No JSON report found")
        exit(1)
    latest = sorted(files)[-1]
    json_path = os.path.join(reports_dir, latest)
else:
    with open(MARKER) as f:
        json_path = f.read().strip()

print(f"Loading: {json_path}")
with open(json_path) as f:
    data = json.load(f)

# ── 2. Japanese keyword -> Vietnamese title map (specificity-ordered) ────
TITLE_MAP = [
    # 2026-09-19 batch: audit_fallback_jobs.py caught 4 generic fallbacks —
    # 外国人駐在員へのお部屋探しコーディネーター (expat room-finding coordinator,
    # ranked #4 in top_jobs!), 専任ライダー (McDonald's delivery rider),
    # 保育士 (nursery-school teacher, both rejected), and ロボット製造
    # (large-maker robot production, matched only the generic 製造|生産|工場
    # branch). The rest of the batch fixes compound titles where a SECONDARY
    # keyword (検査/梱包) stole the primary function (machine operation /
    # assembly / picking) because it sits higher in the map. All MUST win over
    # the generic catch-alls further down.
    (r'お部屋探し|部屋探し', 'Nhân viên tư vấn tìm phòng cho người nước ngoài (coordinator)'),
    (r'専任ライダー|ライダー', 'Nhân viên giao hàng (rider chuyên trách)'),
    (r'保育士|保育園', 'Giáo viên mầm non (nhân viên trông trẻ)'),
    (r'ロボット.*製造|ロボット製造', 'Công nhân sản xuất robot (nhà máy lớn)'),
    (r'半導体製造装置', 'Công nhân sản xuất linh kiện thiết bị bán dẫn (công việc nhẹ nhàng)'),
    (r'学生服|生地の製造', 'Vận hành máy sản xuất vải may đồng phục học sinh (kèm kiểm tra)'),
    (r'製造オペレーター.*検査|製造オペ.*検査', 'Vận hành máy sản xuất & kiểm tra linh kiện kim loại'),
    (r'家電部品.*機械操作', 'Vận hành máy & kiểm tra ngoại quan linh kiện gia dụng'),
    (r'家電部品.*ピッキング|ピッキング.*加工', 'Nhân viên nhặt hàng & gia công linh kiện gia dụng'),
    (r'ピッキング.*梱包|梱包.*ピッキング', 'Nhân viên nhặt hàng & đóng gói trong kho'),
    (r'パーツ組立', 'Công nhân lắp ráp & kiểm tra linh kiện ô tô'),
    (r'自動車の検査|検査.*塗装', 'Công nhân kiểm tra, sơn, lắp ráp linh kiện ô tô'),
    (r'医療用ゴム', 'Công nhân gia công & vận chuyển sản phẩm cao su y tế'),
    (r'製鉄所|エネルギー供給', 'Vận hành thiết bị cung cấp năng lượng trong nhà máy thép'),
    (r'石炭の加工', 'Công nhân gia công & vận chuyển than (than đá)'),
    (r'原料の入出荷|入出荷', 'Nhân viên xuất nhập nguyên liệu & lái xe nâng'),
    (r'採取|測定', 'Nhân viên lấy mẫu, vận chuyển & đo lường than'),
    (r'バイク部品.*鋳造|鋳造', 'Công nhân đúc & gia công linh kiện xe máy'),
    (r'溶接補助', 'Phụ hàn linh kiện máy móc (hỗ trợ thợ hàn)'),
    # 2026-09-13 batch: very specific patterns that MUST win over the generic
    # 製造|生産|工場 and 製造.*オペ catch-alls. 日本語教員 (Japanese-language
    # teacher) fell through to 'Nhân viên sản xuất' and ranked into BOTH
    # top_jobs and priority_jobs; 繊維製造/毛織物 (textile) and
    # 石炭の製造オペレーター (coal) got generic factory titles/descriptions;
    # 製造装置設計技術者 got the generic 製造 WN. Placed at the very top
    # because these strings are unambiguous and must pre-empt the generics.
    (r'日本語教員|日本語教師|日本語講師', 'Giáo viên dạy tiếng Nhật'),
    (r'製造装置設計', 'Kỹ sư thiết kế thiết bị sản xuất'),
    (r'毛織物|繊維製造', 'Công nhân sản xuất hàng dệt may (textile)'),
    (r'石炭.*オペ|石炭の製造', 'Vận hành máy sản xuất than (than đá/coal)'),
    (r'フロア担当|フロアスタッフ', 'Nhân viên phục vụ sàn (cửa hàng)'),
    (r'フォークリフト|フォークリフ', 'Lái xe nâng'),
    (r'リーチリフト', 'Lái xe nâng dạng vươn tới (Reach lift)'),
    (r'マシニングセンタ', 'Vận hành trung tâm gia công CNC'),
    (r'NC旋盤|旋盤', 'Thợ tiện NC'),
    (r'溶接', 'Thợ hàn'),
    (r'塗装', 'Thợ sơn'),
    (r'クレーン', 'Thợ vận hành cần cẩu'),
    (r'品質管理|品質保証', 'Nhân viên quản lý chất lượng'),
    (r'生産技術', 'Kỹ thuật sản xuất'),
    (r'CAD.*設計|設計.*CAD', 'Thiết kế CAD / kỹ thuật'),
    (r'設計', 'Nhân viên thiết kế kỹ thuật'),
    (r'電気保全|機械保全|設備保全', 'Nhân viên bảo trì thiết bị'),
    (r'電気回路|制御', 'Kỹ thuật điện / điều khiển'),
    (r'メンテナンス|保全|保守', 'Nhân viên bảo trì'),
    (r'検査|検品|検查', 'Nhân viên kiểm tra chất lượng'),
    (r'分析', 'Nhân viên phân tích'),
    (r'組立|組み立て', 'Công nhân lắp ráp'),
    (r'梱包|包装', 'Nhân viên đóng gói'),
    (r'加工', 'Công nhân gia công'),
    (r'製造.*オペ|製造オペレーター|生産オペ', 'Vận hành máy sản xuất'),
    (r'オペレーター', 'Vận hành máy móc'),
    # Product-context patterns — MUST come BEFORE the generic 製造|生産|工場
    # catch-all or they collapse to 'Nhân viên sản xuất'. These are recurring
    # UTエージェント/HelloWork/工場ワークス job patterns that used to fall
    # through to the misleading generic fallback (fixed 2026-08-14).
    (r'プラスチック部品.*機械操作', 'Vận hành máy sản xuất linh kiện nhựa'),
    (r'プラスチック部品', 'Công nhân sản xuất linh kiện nhựa'),
    (r'自動車部品', 'Công nhân dây chuyền sản xuất linh kiện ô tô'),
    (r'コンベヤベルト|コンベアベルト', 'Công nhân sản xuất băng tải (conveyor)'),
    (r'活性炭', 'Nhân viên vận chuyển than hoạt tính'),
    (r'航空機', 'Công nhân sản xuất máy bay / linh kiện hàng không'),
    (r'軽作業', 'Công nhân làm công việc nhẹ nhàng (light work)'),
    # 2026-08-20 batch: HelloWork/工場ワークス/JOB Harima non-factory or
    # niche patterns that still fell through to the generic fallback and
    # ranked into top/priority sections. MUST stay before 製造|生産|工場.
    (r'鉄製品製造の機械操作', 'Vận hành máy sản xuất sản phẩm sắt thép'),
    (r'補修作業.*環境整備', 'Nhân viên hỗ trợ sản xuất (sửa chữa, bảo trì môi trường làm việc)'),
    (r'とび工|とび職', 'Thợ tobi (lắp dựng giàn giáo, xây dựng)'),
    (r'組合運営・管理', 'Nhân viên vận hành & quản lý hợp tác xã'),
    (r'商品管理業務', 'Nhân viên quản lý hàng hóa (hướng tới vị trí quản lý)'),
    (r'採用情報', 'Thông tin tuyển dụng (trang tổng hợp)'),
    # 2026-08-26 batch: 工場ワークス/UTエージェント/HelloWork patterns that
    # still fell through to the generic fallback even with a fresh deploy.
    # 大手鉄鋼メーカー affiliate ranked #5 in top_jobs; バイク部品の成型 landed
    # in factory_warehouse_jobs. MUST stay before 製造|生産|工場.
    (r'大手鉄鋼メーカー|鉄鋼メーカー', 'Nhân viên sản xuất tại công ty liên kết hãng thép lớn (chuyển chính thức sau 3-6 tháng)'),
    (r'バイク部品.*成型', 'Công nhân ép khuôn (molding) linh kiện xe máy'),
    (r'バイク部品', 'Công nhân sản xuất linh kiện xe máy'),
    (r'半導体', 'Nhân viên đánh giá, kiểm tra bảng mạch bán dẫn'),
    (r'コンテナ.*積込|積込', 'Công nhân xếp hàng lên container'),
    (r'お菓子', 'Công nhân đóng gói bánh kẹo'),
    (r'家事・使用人', 'Nhân viên giúp việc gia đình'),
    # 2026-09-01 batch: non-factory pass-throughs + niche patterns that still
    # fell through to the generic fallback. 廃棄物処理施設 ranked into
    # top_jobs/priority_jobs; ニチイ (care night staff) ×4, ガスタービン点検,
    # 家具のリース fell through too. MUST stay before 製造|生産|工場.
    (r'廃棄物処理施設|廃棄物', 'Nhân viên vận hành & quản lý thiết bị cơ sở xử lý chất thải (công trình công cộng)'),
    (r'ニチイ', 'Nhân viên trực đêm tại trung tâm chăm sóc (Nichii)'),
    (r'ガスタービン', 'Nhân viên kiểm tra, ghi chép linh kiện tua-bin khí (gas turbine)'),
    (r'家具のリース|家具リース', 'Nhân viên tư vấn cho thuê nội thất (dành cho người nước ngoài)'),
    # 2026-09-07 batch: new fallback patterns caught by audit_fallback_jobs.py.
    # 人事採用業務 + 外国人材採用コンサルティング are HelloWork 正社員 office/HR
    # pass-throughs that ranked into top_jobs/priority_jobs; 流体機器の実験作業,
    # アルミ部品のチェック/洗浄 and 食品工場で洗浄 are real factory/technical jobs
    # whose keywords (実験/洗浄/チェック/アルミ) were missing from the map.
    # MUST stay before 製造職|製造|生産|工場 catch-alls (食品工場 contains 工場).
    (r'人事採用業務|人事採用', 'Nhân viên phụ trách nhân sự - tuyển dụng (văn phòng)'),
    (r'外国人材採用コンサルティング', 'Nhân viên tư vấn tuyển dụng nhân sự nước ngoài'),
    (r'流体機器の実験|流体機器', 'Nhân viên thử nghiệm thiết bị thủy lực (fluid equipment)'),
    (r'食品工場.*洗浄|洗浄.*食品工場', 'Công nhân vệ sinh nhà máy thực phẩm'),
    (r'アルミ部品', 'Công nhân kiểm tra, vệ sinh linh kiện nhôm'),
    (r'洗浄', 'Công nhân vệ sinh công nghiệp (tẩy rửa)'),
    (r'製造職.*夜勤|夜勤.*製造職', 'Nhân viên sản xuất (có ca đêm)'),
    (r'製造職', 'Nhân viên sản xuất'),
    (r'製造|生産|工場', 'Nhân viên sản xuất'),
    (r'ピッキング', 'Nhân viên nhặt hàng'),
    (r'入出庫|出庫|入庫', 'Nhân viên xuất nhập kho'),
    (r'倉庫|物流|配送センター', 'Nhân viên kho / logistics'),
    (r'配達|配送|宅配', 'Nhân viên giao hàng'),
    (r'選別', 'Nhân viên phân loại'),
    (r'計測', 'Nhân viên đo lường'),
    (r'出荷', 'Nhân viên xuất hàng'),
    (r'石炭|コークス', 'Nhân viên sản xuất than cốc'),
    (r'取付', 'Nhân viên lắp đặt'),
    (r'電気|電子', 'Nhân viên điện / điện tử'),
    (r'監視|操業', 'Nhân viên giám sát vận hành'),
    (r'AIエンジニア|ＡＩエンジニア|AI エンジニア', 'Kỹ sư AI'),
    (r'エンジニア', 'Kỹ sư'),
    (r'コンビニ', 'Nhân viên cửa hàng tiện lợi'),
    (r'ホールスタッフ|ホール・スタッフ', 'Phục vụ nhà hàng'),
    (r'ベトナム.*通訳|通訳.*ベトナム', 'Phiên dịch tiếng Việt'),
    (r'通訳|翻訳', 'Phiên dịch / biên dịch'),
    (r'事務', 'Nhân viên văn phòng'),
    (r'清掃|掃除', 'Nhân viên vệ sinh'),
    (r'営業', 'Nhân viên kinh doanh'),
    (r'警備|ガード|警備員', 'Nhân viên bảo vệ'),
    (r'運転|ドライバー', 'Lái xe'),
    (r'食品.*製造|食品加工', 'Nhân viên chế biến thực phẩm'),
    (r'生活支援員', 'Nhân viên hỗ trợ sinh hoạt (chăm sóc)'),
    (r'ダクト設備工事|ダクト工事', 'Công nhân thi công lắp đặt ống dẫn khí (duct)'),
]

def translate_title(jp_title):
    # Compound title pre-check: titles with "・" (nakaguro) list multiple
    # functions. The regex map may pick the wrong primary keyword (e.g.
    # 検査 before 組立). Handle these explicitly FIRST.
    if "・" in jp_title:
        # 2026-09-19: machine-design/build listing that stacks three duties
        # (CAD design ・ electrical-control design ・ metal processing &
        # assembly). Must pre-empt the 加工.*組立 branch below, which would
        # otherwise return the generic 'Công nhân gia công, lắp ráp, kiểm tra'.
        if re.search(r'省力化装置|装置のCAD設計|装置組立て', jp_title):
            return 'Nhân viên thiết kế CAD, chế tạo & lắp ráp máy móc thiết bị (chưa cần kinh nghiệm)'
        # Processing + Assembly + Inspection (e.g. "加工・組立・検査作業")
        if re.search(r'加工.*組立.*検査', jp_title) or re.search(r'加工.*組立', jp_title):
            if '航空' in jp_title or 'エンジン' in jp_title:
                return 'Công nhân gia công, lắp ráp, kiểm tra linh kiện động cơ máy bay'
            return 'Công nhân gia công, lắp ráp, kiểm tra linh kiện'
        # Assembly + Inspection (e.g. "組立・検査")
        if re.search(r'組立.*検査', jp_title):
            if 'ロボット' in jp_title:
                return 'Công nhân lắp ráp robot đa năng'
            if '小型' in jp_title:
                return 'Công nhân lắp ráp, kiểm tra linh kiện nhỏ'
            return 'Công nhân lắp ráp, kiểm tra linh kiện'
        # Molding + Inspection + Packing
        if re.search(r'成形.*検査.*梱包', jp_title):
            return 'Công nhân ép khuôn, kiểm tra, đóng gói'
    
    for pattern, vi in TITLE_MAP:
        if re.search(pattern, jp_title):
            return vi
    return 'Nhân viên sản xuất'

# ── 3. why_notable description generator (match on Japanese title only!) ─
def _format_desc(base, area, emp_type, company=None):
    """Append area/employment type to a description base string."""
    extras = []
    if area:
        extras.append(f'khu vực {area}')
    if emp_type:
        extras.append(f'({emp_type})')
    if extras:
        base += ' - ' + ', '.join(extras)
    return base

def gen_why_notable(job):
    """Generate a specific Vietnamese description. Matches on Japanese title
    to avoid the substring false-positive problem with Vietnamese text."""
    title = job.get('title', '')
    company = job.get('company', '')
    area = job.get('area', '')
    emp_type = job.get('employment_type', '')

    # Compound title pre-check: titles with "・" (nakaguro) may match the
    # wrong keyword (e.g. 検査 before 組立). Handle these explicitly first.
    if "・" in title:
        if re.search(r'省力化装置|装置のCAD設計|装置組立て', title):
            base = f'Cần nhân viên thiết kế CAD, chế tạo và lắp ráp máy móc thiết bị tại {company} — tuyển cả người chưa có kinh nghiệm' if company else 'Cần nhân viên thiết kế CAD, chế tạo và lắp ráp máy móc thiết bị — tuyển cả người chưa có kinh nghiệm'
            return _format_desc(base, area, emp_type, company)
        if re.search(r'加工.*組立.*検査', title):
            if '航空' in title or 'エンジン' in title:
                base = 'Cần công nhân gia công, lắp ráp, kiểm tra linh kiện động cơ máy bay, yêu cầu độ chính xác cao'
            else:
                base = 'Cần công nhân gia công, lắp ráp, kiểm tra linh kiện trong nhà máy'
            return _format_desc(base, area, emp_type, company)
        if re.search(r'組立.*検査', title):
            if 'ロボット' in title:
                base = 'Cần công nhân lắp ráp robot đa năng, kiểm tra chất lượng sản phẩm'
            else:
                base = 'Cần công nhân lắp ráp, kiểm tra linh kiện trong nhà máy'
            return _format_desc(base, area, emp_type, company)
        if re.search(r'成形.*検査.*梱包', title):
            base = 'Cần công nhân ép khuôn, kiểm tra, đóng gói linh kiện'
            return _format_desc(base, area, emp_type, company)
        if re.search(r'製造.*オペ.*検査', title) or re.search(r'製造OP.*検査', title):
            base = 'Cần nhân viên vận hành máy sản xuất, kiểm tra chất lượng sản phẩm'
            return _format_desc(base, area, emp_type, company)
        if re.search(r'塗装.*検査.*組立', title):
            base = 'Cần công nhân sơn, kiểm tra, lắp ráp linh kiện'
            return _format_desc(base, area, emp_type, company)

    # 2026-09-19 batch (mirrors the TITLE_MAP additions at the top of the map):
    # the 4 audit fallbacks + the compound-title fixes. MUST stay before the
    # generic 製造|生産|工場 / 検査 branches below.
    if re.search(r'お部屋探し|部屋探し', title):
        base = f'Cần nhân viên tư vấn, hỗ trợ tìm phòng trọ cho người nước ngoài (coordinator) tại {company} — tính chất dịch vụ/tư vấn, KHÔNG phải sản xuất' if company else 'Cần nhân viên tư vấn, hỗ trợ tìm phòng trọ cho người nước ngoài (coordinator) — tính chất dịch vụ/tư vấn, KHÔNG phải sản xuất'
        return _format_desc(base, area, emp_type, company)
    elif re.search(r'専任ライダー|ライダー', title):
        base = f'Cần nhân viên giao hàng (rider chuyên trách) tại {company} — giao đồ ăn, KHÔNG phải sản xuất nhà máy' if company else 'Cần nhân viên giao hàng (rider chuyên trách) — KHÔNG phải sản xuất nhà máy'
        return _format_desc(base, area, emp_type, company)
    elif re.search(r'保育士|保育園', title):
        base = f'Cần giáo viên mầm non (trông trẻ) tại {company} — tính chất giáo dục/chăm sóc, KHÔNG phải sản xuất' if company else 'Cần giáo viên mầm non (trông trẻ) — tính chất giáo dục/chăm sóc, KHÔNG phải sản xuất'
        return _format_desc(base, area, emp_type, company)
    elif re.search(r'ロボット.*製造|ロボット製造', title):
        base = 'Cần công nhân sản xuất robot tại nhà máy của hãng lớn — có xe bus trực tiếp từ ga Akashi, phụ cấp chuyên cần tới 3 man, thu nhập tới 32 man/tháng, ca ngày, nghỉ T7-CN-lễ, chưa cần kinh nghiệm'
        return _format_desc(base, area, emp_type, company)
    elif re.search(r'半導体製造装置', title):
        base = 'Cần công nhân sản xuất linh kiện thiết bị bán dẫn tại nhà máy mới — công việc nhẹ nhàng, môi trường sạch sẽ, nghỉ T7-CN-lễ'
        return _format_desc(base, area, emp_type, company)
    elif re.search(r'学生服|生地の製造', title):
        base = 'Cần nhân viên vận hành máy sản xuất vải may đồng phục học sinh, kèm kiểm tra sản phẩm — làm ca luân phiên, chưa cần kinh nghiệm'
        return _format_desc(base, area, emp_type, company)
    elif re.search(r'製造オペレーター.*検査|製造オペ.*検査', title):
        base = f'Cần nhân viên vận hành máy sản xuất và kiểm tra linh kiện kim loại tại {company} — có cơ hội chuyển sang hợp đồng trực tiếp' if company else 'Cần nhân viên vận hành máy sản xuất và kiểm tra linh kiện kim loại — có cơ hội chuyển sang hợp đồng trực tiếp'
        return _format_desc(base, area, emp_type, company)
    elif re.search(r'家電部品.*機械操作', title):
        base = 'Cần nhân viên vận hành máy và kiểm tra ngoại quan linh kiện thiết bị gia dụng — ca ngày, nghỉ T7-CN'
        return _format_desc(base, area, emp_type, company)
    elif re.search(r'家電部品.*ピッキング|ピッキング.*加工', title):
        base = 'Cần nhân viên nhặt hàng và gia công linh kiện thiết bị gia dụng — ca đêm chuyên trách, nghỉ T7-CN, thu nhập tới 27 man/tháng'
        return _format_desc(base, area, emp_type, company)
    elif re.search(r'ピッキング.*梱包|梱包.*ピッキング', title):
        base = 'Cần nhân viên nhặt hàng & đóng gói trong kho — ca ngày, ga cách 10 phút đi bộ, có chế độ trả lương theo ngày'
        return _format_desc(base, area, emp_type, company)
    elif re.search(r'パーツ組立', title):
        base = 'Cần công nhân lắp ráp và kiểm tra linh kiện ô tô — ca ngày, có hỗ trợ nhà ở, công việc ổn định lâu dài'
        return _format_desc(base, area, emp_type, company)
    elif re.search(r'自動車の検査|検査.*塗装', title):
        base = 'Cần công nhân kiểm tra, sơn, lắp ráp linh kiện ô tô — có thưởng theo chiến dịch, ký túc xá miễn phí, lương giờ 1.900 yên'
        return _format_desc(base, area, emp_type, company)
    elif re.search(r'医療用ゴム', title):
        base = 'Cần công nhân gia công & vận chuyển sản phẩm cao su y tế — lương giờ 1.570 yên, trả đủ chi phí đi lại, đi làm bằng ô tô/xe máy được, có xe đưa đón miễn phí, làm 3 ca'
        return _format_desc(base, area, emp_type, company)
    elif re.search(r'製鉄所|エネルギー供給', title):
        base = 'Cần nhân viên vận hành thiết bị cung cấp năng lượng trong nhà máy thép — có xe bus miễn phí từ ga JR Kakogawa, hỗ trợ chi phí đi lại cho người ở xa, phòng máy lạnh, ít tăng ca, có chế độ trả lương theo ngày'
        return _format_desc(base, area, emp_type, company)
    elif re.search(r'石炭の加工', title):
        base = 'Cần công nhân gia công & vận chuyển than (than đá) — lương giờ 1.550 yên, ca ngày, nghỉ T7-CN-lễ, chấp nhận người chưa có kinh nghiệm'
        return _format_desc(base, area, emp_type, company)
    elif re.search(r'原料の入出荷|入出荷', title):
        base = 'Cần nhân viên xuất nhập nguyên liệu và vận hành xe nâng — lương giờ 1.500 yên, có ký túc xá, thu nhập từ 23,6 man/tháng'
        return _format_desc(base, area, emp_type, company)
    elif re.search(r'採取|測定', title):
        base = 'Cần nhân viên lấy mẫu, vận chuyển và đo lường than — làm 4 ngày nghỉ 2 ngày, có xe đưa đón, chưa cần kinh nghiệm'
        return _format_desc(base, area, emp_type, company)
    elif re.search(r'バイク部品.*鋳造|鋳造', title):
        base = 'Cần công nhân đúc và gia công linh kiện xe máy — có ký túc xá, trả lương theo tuần, chưa cần kinh nghiệm'
        return _format_desc(base, area, emp_type, company)
    elif re.search(r'溶接補助', title):
        base = 'Cần phụ hàn (hỗ trợ hàn) linh kiện máy móc — lương giờ 1.450 yên, có ký túc xá, thu nhập từ 27,9 man/tháng'
        return _format_desc(base, area, emp_type, company)
    # Pattern-order matches TITLE_MAP but with descriptions
    # 2026-09-13 batch (mirrors the TITLE_MAP additions at the top of the map):
    # these MUST come before the 製造|生産|工場 and 製造.*オペ branches below,
    # otherwise their generic output is generated again.
    if re.search(r'日本語教員|日本語教師|日本語講師', title):
        base = f'Cần giáo viên dạy tiếng Nhật tại {company} — tính chất giáo dục/giảng dạy, KHÔNG phải sản xuất' if company else 'Cần giáo viên dạy tiếng Nhật — tính chất giáo dục/giảng dạy, KHÔNG phải sản xuất'
    elif re.search(r'製造装置設計', title):
        base = f'Cần kỹ sư thiết kế thiết bị, máy móc sản xuất tại {company} — vị trí kỹ thuật, cần chuyên môn' if company else 'Cần kỹ sư thiết kế thiết bị, máy móc sản xuất — vị trí kỹ thuật, cần chuyên môn'
    elif re.search(r'毛織物|繊維製造', title):
        base = 'Cần công nhân nhà máy dệt may: chuẩn bị sợi, vận hành máy — không cần kinh nghiệm, lương giờ 1.500 yên, ít tăng ca'
    elif re.search(r'石炭.*オペ|石炭の製造', title):
        base = f'Cần nhân viên vận hành máy sản xuất than (than đá/coal) tại {company}, làm 3 ca luân phiên, lương giờ 1.600 yên, không cần kinh nghiệm' if company else 'Cần nhân viên vận hành máy sản xuất than (than đá/coal), làm 3 ca luân phiên, lương giờ 1.600 yên, không cần kinh nghiệm'
    elif re.search(r'フロア担当|フロアスタッフ', title):
        base = f'Cần nhân viên phục vụ sàn cửa hàng tại {company} (không phải sản xuất)' if company else 'Cần nhân viên phục vụ sàn cửa hàng (không phải sản xuất)'
    elif re.search(r'溶接', title):
        base = f'Cần thợ hàn lành nghề tại {company}' if company else 'Cần thợ hàn lành nghề'
    elif re.search(r'フォークリフト|フォーク', title):
        base = f'Cần lái xe nâng có kinh nghiệm tại {company}' if company else 'Cần lái xe nâng có kinh nghiệm'
    elif re.search(r'NC旋盤|旋盤|マシニング', title):
        base = f'Cần thợ gia công CNC / tiện phay tại {company}' if company else 'Cần thợ gia công CNC / tiện phay'
    elif re.search(r'塗装', title):
        base = f'Cần thợ sơn công nghiệp tại {company}' if company else 'Cần thợ sơn công nghiệp'
    elif re.search(r'メンテナンス|保全|保守', title):
        base = f'Cần nhân viên bảo trì thiết bị tại {company}' if company else 'Cần nhân viên bảo trì thiết bị'
    elif re.search(r'検査|検品', title):
        base = f'Cần nhân viên kiểm tra chất lượng sản phẩm tại {company}' if company else 'Cần nhân viên kiểm tra chất lượng sản phẩm'
    elif re.search(r'組立|組み立て', title):
        base = f'Cần công nhân lắp ráp linh kiện tại {company}' if company else 'Cần công nhân lắp ráp linh kiện'
    elif re.search(r'プラスチック部品.*機械操作', title):
        base = f'Cần nhân viên vận hành máy sản xuất linh kiện nhựa tại {company}' if company else 'Cần nhân viên vận hành máy sản xuất linh kiện nhựa'
    elif re.search(r'プラスチック部品', title):
        base = f'Cần công nhân sản xuất linh kiện nhựa tại {company}' if company else 'Cần công nhân sản xuất linh kiện nhựa'
    elif re.search(r'自動車部品', title):
        base = f'Cần công nhân làm việc trên dây chuyền sản xuất linh kiện ô tô tại {company}' if company else 'Cần công nhân làm việc trên dây chuyền sản xuất linh kiện ô tô'
    elif re.search(r'コンベヤベルト|コンベアベルト', title):
        base = f'Cần công nhân sản xuất băng tải công nghiệp tại {company}' if company else 'Cần công nhân sản xuất băng tải công nghiệp'
    elif re.search(r'活性炭', title):
        if '有資格者' in title:
            base = 'Cần nhân viên vận chuyển than hoạt tính (yêu cầu có chứng chỉ)'
        else:
            base = 'Cần nhân viên vận chuyển than hoạt tính'
    elif re.search(r'航空機', title):
        base = f'Cần công nhân tham gia sản xuất máy bay tại {company}' if company else 'Cần công nhân tham gia sản xuất máy bay'
    elif re.search(r'軽作業', title):
        base = 'Cần nhân viên làm các công việc nhẹ nhàng tại nhà máy, không bê vác vật nặng'
    elif re.search(r'鉄製品製造の機械操作', title):
        base = 'Cần nhân viên vận hành máy móc trong dây chuyền sản xuất sản phẩm sắt thép, làm ngày, có ký túc xá'
    elif re.search(r'補修作業.*環境整備', title):
        base = 'Cần nhân viên hỗ trợ sản xuất tại nhà máy: sửa chữa nhỏ và vệ sinh, bảo trì môi trường làm việc'
    elif re.search(r'とび工|とび職', title):
        base = 'Cần thợ tobi — lắp dựng giàn giáo, thao tác trên cao trong lĩnh vực xây dựng (tính chất công trường, không phải nhà máy)'
    elif re.search(r'組合運営・管理', title):
        base = 'Cần nhân viên vận hành, quản lý hợp tác xã (tính chất hành chính/quản lý, không phải sản xuất)'
    elif re.search(r'商品管理業務', title):
        base = 'Cần nhân viên quản lý hàng hóa/tồn kho, lộ trình lên vị trí quản lý, có thể đi làm bằng ô tô riêng'
    elif re.search(r'採用情報', title):
        base = 'Trang thông tin tuyển dụng chung (không phải vị trí cụ thể) — nên xem chi tiết trực tiếp trên trang nguồn'
    elif re.search(r'大手鉄鋼メーカー|鉄鋼メーカー', title):
        base = 'Làm việc tại công ty liên kết của hãng thép lớn, theo chế độ giới thiệu chuyển chính thức sau 3-6 tháng. Chỉ làm ca ngày, nghỉ 118 ngày/năm, lương giờ 1.500 yên, không cần hồ sơ xin việc, chấp nhận người chưa có kinh nghiệm'
    elif re.search(r'バイク部品.*成型', title):
        base = 'Ép khuôn (molding) linh kiện xe máy, làm 2 ca luân phiên, lương giờ 1.600 yên, chấp nhận người chưa có kinh nghiệm, phỏng vấn online'
    elif re.search(r'半導体', title):
        base = 'Đánh giá, kiểm tra chất lượng bảng mạch bán dẫn. Làm ca ngày, nghỉ thứ 7, Chủ nhật và ngày lễ, có xe đưa đón, thu nhập tới 33 man/tháng'
    elif re.search(r'コンテナ.*積込|積込', title):
        base = 'Xếp hàng lên container, làm ca ngày, có xe đưa đón, ít tăng ca, chấp nhận người chưa có kinh nghiệm'
    elif re.search(r'お菓子', title):
        base = 'Đóng gói bánh kẹo vào hộp, túi. Chỉ làm ca ngày, có thể làm từ 1 ngày/tuần, phù hợp người làm thêm (W-work)'
    elif re.search(r'家事・使用人', title):
        base = 'Công việc giúp việc gia đình, chăm sóc người nước ngoài cao tuổi'
    elif re.search(r'廃棄物処理施設|廃棄物', title):
        base = 'Cần nhân viên vận hành, quản lý thiết bị tại cơ sở xử lý chất thải — công trình công cộng ổn định (không phải sản xuất nhà máy)'
    elif re.search(r'ニチイ', title):
        base = 'Cần nhân viên trực đêm tại trung tâm chăm sóc (care center) Nichii — chăm sóc người cao tuổi (không phải sản xuất)'
    elif re.search(r'ガスタービン', title):
        base = 'Cần nhân viên kiểm tra, ghi chép linh kiện tua-bin khí (gas turbine), trả lương ngày, ít tăng ca, chấp nhận người mới'
    elif re.search(r'家具のリース|家具リース', title):
        base = 'Cần nhân viên tư vấn, giới thiệu dịch vụ cho thuê nội thất cho người nước ngoài (không phải sản xuất)'
    elif re.search(r'人事採用業務|人事採用', title):
        base = 'Cần nhân viên phụ trách mảng nhân sự - tuyển dụng của tổ chức (tính chất văn phòng, không phải sản xuất)'
    elif re.search(r'外国人材採用コンサルティング', title):
        base = 'Cần nhân viên tư vấn tuyển dụng nhân sự người nước ngoài cho doanh nghiệp (công việc văn phòng/tư vấn, không phải sản xuất)'
    elif re.search(r'流体機器の実験|流体機器', title):
        base = 'Cần nhân viên làm thí nghiệm, thử nghiệm thiết bị chất lỏng (fluid equipment) — tận dụng kinh nghiệm, làm ngày, nghỉ T7-CN & lễ, lương tháng tới 46 man'
    elif re.search(r'食品工場.*洗浄|洗浄.*食品工場', title):
        base = 'Cần công nhân vệ sinh (rửa) tại nhà máy thực phẩm lớn — làm 2 tiếng/ngày, ca tối, phù hợp người muốn làm thêm trong diện miễn thuế (扶養内)'
    elif re.search(r'アルミ部品', title):
        base = 'Cần công nhân kiểm tra linh kiện nhôm & vệ sinh (rửa) — làm ngày, nghỉ T7-CN & lễ, lương giờ 1.600 yên'
    elif re.search(r'洗浄', title):
        base = 'Cần công nhân làm công việc vệ sinh, tẩy rửa thiết bị tại nhà máy'
    elif re.search(r'製造職.*夜勤|夜勤.*製造職', title):
        base = 'Tuyển nhân viên sản xuất (chế tạo) chính thức, có ca đêm, chấp nhận người chưa có kinh nghiệm'
    elif re.search(r'製造職', title):
        base = 'Tuyển nhân viên sản xuất (chế tạo) chính thức, chấp nhận người chưa có kinh nghiệm'
    elif re.search(r'製造|生産|工場', title):
        base = f'Cần nhân viên sản xuất tại nhà máy {company}' if company else 'Cần nhân viên sản xuất tại nhà máy'
    elif re.search(r'加工', title):
        base = f'Cần công nhân gia công chế tạo tại {company}' if company else 'Cần công nhân gia công chế tạo'
    elif re.search(r'倉庫|物流', title):
        base = f'Cần nhân viên kho / logistics tại {company}' if company else 'Cần nhân viên kho / logistics'
    elif re.search(r'オペレーター', title):
        base = f'Cần vận hành máy móc sản xuất tại {company}' if company else 'Cần vận hành máy móc sản xuất'
    elif re.search(r'包装|梱包', title):
        base = f'Cần nhân viên đóng gói tại {company}' if company else 'Cần nhân viên đóng gói'
    elif re.search(r'電気|電子', title):
        base = f'Cần nhân viên kỹ thuật điện/điện tử tại {company}' if company else 'Cần nhân viên kỹ thuật điện/điện tử'
    elif re.search(r'クレーン', title):
        base = f'Cần thợ vận hành cần cẩu tại {company}' if company else 'Cần thợ vận hành cần cẩu'
    elif re.search(r'設計|CAD', title):
        base = f'Cần kỹ sư thiết kế tại {company}' if company else 'Cần kỹ sư thiết kế'
    elif re.search(r'品質管理|品質保証', title):
        base = f'Cần nhân viên quản lý chất lượng tại {company}' if company else 'Cần nhân viên quản lý chất lượng'
    elif re.search(r'食品', title):
        base = f'Cần nhân viên chế biến thực phẩm tại {company}' if company else 'Cần nhân viên chế biến thực phẩm'
    elif re.search(r'ピッキング|出庫|入出庫', title):
        base = f'Cần nhân viên kho vận tại {company}' if company else 'Cần nhân viên kho vận'
    elif re.search(r'配達|配送|宅配', title):
        base = f'Cần nhân viên giao hàng tại {company}' if company else 'Cần nhân viên giao hàng'
    elif re.search(r'営業', title):
        base = f'Cần nhân viên kinh doanh tại {company}' if company else 'Cần nhân viên kinh doanh'
    elif re.search(r'AI|ＡＩ|エンジニア', title):
        base = f'Cần kỹ sư công nghệ tại {company}' if company else 'Cần kỹ sư công nghệ'
    elif re.search(r'通訳|翻訳|ベトナム', title):
        base = f'Cần phiên dịch viên tại {company}' if company else 'Cần phiên dịch viên'
    elif re.search(r'取付|据付', title):
        base = f'Cần nhân viên lắp đặt thiết bị tại {company}' if company else 'Cần nhân viên lắp đặt thiết bị'
    elif re.search(r'選別', title):
        base = f'Cần nhân viên phân loại sản phẩm tại {company}' if company else 'Cần nhân viên phân loại sản phẩm'
    elif re.search(r'計測', title):
        base = f'Cần nhân viên đo lường kiểm tra tại {company}' if company else 'Cần nhân viên đo lường kiểm tra'
    elif re.search(r'出荷', title):
        base = f'Cần nhân viên xuất hàng tại {company}' if company else 'Cần nhân viên xuất hàng'
    elif re.search(r'分析', title):
        base = f'Cần nhân viên phân tích tại {company}' if company else 'Cần nhân viên phân tích'
    elif re.search(r'石炭|コークス', title):
        base = f'Cần nhân viên sản xuất than cốc tại {company}' if company else 'Cần nhân viên sản xuất than cốc'
    elif re.search(r'監視|操業', title):
        base = f'Cần nhân viên giám sát vận hành tại {company}' if company else 'Cần nhân viên giám sát vận hành'
    elif re.search(r'警備|ガード', title):
        base = f'Cần nhân viên bảo vệ tại {company}' if company else 'Cần nhân viên bảo vệ'
    elif re.search(r'清掃', title):
        base = f'Cần nhân viên vệ sinh công nghiệp tại {company}' if company else 'Cần nhân viên vệ sinh công nghiệp'
    elif re.search(r'コンビニ', title):
        base = f'Cần nhân viên cửa hàng tiện lợi tại {company}' if company else 'Cần nhân viên cửa hàng tiện lợi'
    elif re.search(r'ホール', title):
        base = f'Cần nhân viên phục vụ tại {company}' if company else 'Cần nhân viên phục vụ'
    elif re.search(r'生活支援員', title):
        base = f'Cần nhân viên hỗ trợ sinh hoạt, chăm sóc người khuyết tật/người cao tuổi tại {company}' if company else 'Cần nhân viên hỗ trợ sinh hoạt, chăm sóc người khuyết tật/người cao tuổi tại cơ sở trợ giúp'
    elif re.search(r'ダクト設備工事', title):
        base = f'Cần công nhân thi công, lắp đặt hệ thống ống dẫn khí (duct) tại {company}' if company else 'Cần công nhân thi công, lắp đặt hệ thống ống dẫn khí (duct), chấp nhận người chưa có kinh nghiệm'
    else:
        base = f'Cần công nhân làm việc tại nhà máy {company}' if company else 'Cần công nhân làm việc tại nhà máy'

    extras = []
    if area and area not in base:
        extras.append(f'khu vực {area}')
    if emp_type and emp_type not in base:
        extras.append(f'({emp_type})')
    if extras:
        base += ' - ' + ', '.join(extras)
    return base

# ── 4. Process all jobs ──────────────────────────────────────────────────
total = len(data['all_jobs'])
for job in data['all_jobs']:
    title = job.get('title', '')
    job['title_vi'] = translate_title(title)
    existing = job.get('why_notable', '')
    # 2026-09-19: titles fixed by the newest pattern batch keep their old
    # (semantically OK but mismatched) description because it does not start
    # with a generic prefix. Force regeneration for those so title_vi and
    # why_notable stay consistent.
    force_regen = re.search(r'お部屋探し|専任ライダー|保育士|ロボット.*製造|半導体製造装置|学生服|製造オペレーター.*検査|家電部品.*機械操作|家電部品.*ピッキング|ピッキング.*梱包|パーツ組立|自動車の検査|医療用ゴム|製鉄所|石炭の加工|入出荷|採取|鋳造|溶接補助|省力化装置', title)
    # Regenerate when the existing description is one of the generic outputs:
    # the PIPELINE's rule-based prefixes ('Cần tuyển…'), the fallback prefix
    # ('Cần công nhân làm việc tại nhà máy…'), or gen_why_notable's OWN
    # 製造|生産|工場 generic output ('Cần nhân viên sản xuất tại nhà máy…').
    # The last one matters: niche factory titles containing 工場 (e.g.
    # 食品工場で洗浄作業) can get the generic WN on a first pass and then a
    # NEW specific TITLE_MAP/gen_why_notable pattern is baked in — without
    # this prefix the stale generic WN would survive the re-run (2026-09-07).
    if (not existing or force_regen
            or existing.startswith('Cần tuyển')
            or existing.startswith('Cần công nhân làm việc tại nhà máy')
            or existing.startswith('Cần nhân viên sản xuất tại nhà máy')):
        job['why_notable'] = gen_why_notable(job)

print(f"Translated {total} jobs in all_jobs[]")

# ── 5. Pass 4: Propagate why_notable to category sections ────────────────
notable_map = {j["id"]: j.get("why_notable", "") for j in data["all_jobs"]}
title_map = {j["id"]: j.get("title_vi", "") for j in data["all_jobs"]}
section_keys = ["top_jobs", "priority_jobs", "engineer_jobs",
                "factory_warehouse_jobs", "large_factory_jobs"]

prop_wn = 0
prop_tvi = 0
for sk in section_keys:
    if sk in data:
        for job in data[sk]:
            jid = job["id"]
            if jid in notable_map and notable_map[jid]:
                if job.get("why_notable") != notable_map[jid]:
                    job["why_notable"] = notable_map[jid]
                    prop_wn += 1
            if jid in title_map and title_map[jid]:
                if job.get("title_vi") != title_map[jid]:
                    job["title_vi"] = title_map[jid]
                    prop_tvi += 1

print(f"Propagated why_notable to {prop_wn} jobs across category sections")
print(f"Synced title_vi to {prop_tvi} jobs across category sections")

# ── 6. Save ──────────────────────────────────────────────────────────────
with open(json_path, "w") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"Saved to {json_path}")

# ── 7. Quick verification ────────────────────────────────────────────────
for sk in section_keys:
    if sk in data:
        jobs = data[sk]
        tvi = sum(1 for j in jobs if j.get('title_vi'))
        wn = sum(1 for j in jobs if j.get('why_notable'))
        print(f"  {sk}: {len(jobs)} jobs, title_vi={tvi}/{len(jobs)}, why_notable={wn}/{len(jobs)}")

print("Agent review complete.")
