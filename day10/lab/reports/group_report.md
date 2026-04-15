# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** CS & IT Helpdesk Team  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Member 1 | Ingestion / Raw Owner | member1@example.com |
| Member 2 | Cleaning & Quality Owner | member2@example.com |
| Member 3 | Embed & Idempotency Owner | member3@example.com |
| Member 4 | Monitoring / Docs Owner | member4@example.com |

**Ngày nộp:** 2026-04-15  
**Repo:** Lecture-Day-08-09-10  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md` (code/trace sớm; report có thể muộn hơn nếu được phép).  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after** (CSV eval hoặc screenshot).

---

## 1. Pipeline tổng quan (150–200 từ)

> Nguồn raw là gì (CSV mẫu / export thật)? Chuỗi lệnh chạy end-to-end? `run_id` lấy ở đâu trong log?

**Tóm tắt luồng:**

Nguồn raw là file CSV mẫu `data/raw/policy_export_dirty.csv` chứa 10 dòng export có cố ý "bẩn": duplicate chunk (dòng 2), chunk refund stale 14 ngày (dòng 3), dòng thiếu text và ngày (dòng 5), bản HR cũ 2025 (dòng 7), doc_id lạ `legacy_catalog_xyz_zzz` (dòng 9), và ngày DD/MM/YYYY (dòng 10).

Pipeline thực hiện chuỗi: **ingest** (đọc CSV) → **clean** (9 rules: allowlist doc_id, normalize date, quarantine HR stale, quarantine empty text, quarantine empty exported_at, dedupe, normalize Unicode, fix refund 14→7, strip annotations) → **validate** (8 expectations: 6 halt + 2 warn) → **embed** (upsert ChromaDB với prune stale IDs) → **monitor** (freshness SLA + ingest→publish lag).

`run_id` được ghi trong **dòng đầu log** (`artifacts/logs/run_<id>.log`), trong **manifest JSON** (`artifacts/manifests/manifest_<id>.json`), và trên **metadata mỗi vector** trong Chroma collection.

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**

```bash
python etl_pipeline.py run --run-id clean-final
```

---

## 2. Cleaning & expectation (150–200 từ)

> Baseline đã có nhiều rule (allowlist, ngày ISO, HR stale, refund, dedupe…). Nhóm thêm **≥3 rule mới** + **≥2 expectation mới**. Khai báo expectation nào **halt**.

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| `normalize_unicode` (rule) | chunk_text chứa BOM/NBSP khi inject | chunk_text clean, chunk_id thay đổi (hash khác) | `cleaning_rules.py` L141-143, inject test với BOM char |
| `quarantine_empty_exported_at` (rule) | Inject row exported_at="" → cleaned_records +1 | quarantine_records +1, cleaned_records -1 | `cleaning_rules.py` L131-134, quarantine CSV cột reason="missing_exported_at" |
| `strip_internal_annotations` (rule) | chunk_text row 3 chứa "(ghi chú: bản sync cũ...)" + "[cleaned: stale_refund_window]" | text stripped → chunk_id thay đổi, embedding chất lượng hơn | `cleaning_rules.py` L150-152, diff cleaned CSV clean-run-01 vs inject |
| `no_empty_exported_at` (expectation, **warn**) | Inject empty exported_at → warn triggered | Tất cả cleaned rows có exported_at → OK | `expectations.py` E7, log expectation line |
| `chunk_max_length_2000` (expectation, **halt**) | Inject chunk >2000 chars → halt | Tất cả sample chunks <2000 → OK | `expectations.py` E8, log expectation line |

**Rule chính (baseline + mở rộng):**

- **Baseline (6):** allowlist doc_id, normalize effective_date, quarantine HR stale, quarantine empty text, dedupe, fix refund 14→7.
- **Mới (3):** quarantine empty exported_at, normalize Unicode BOM/zero-width/NBSP, strip internal annotations (ghi chú/cleaned tags).
- **Expectations baseline (6):** min_one_row (halt), no_empty_doc_id (halt), refund_no_stale_14d_window (halt), chunk_min_length_8 (warn), effective_date_iso (halt), hr_leave_no_stale_10d_annual (halt).
- **Expectations mới (2):** no_empty_exported_at (warn), chunk_max_length_2000 (halt).

**Ví dụ 1 lần expectation fail (nếu có) và cách xử lý:**

Sprint 3 inject: `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`  
→ `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`  
→ Pipeline hiện `WARN: expectation failed but --skip-validate → tiếp tục embed (chỉ dùng cho demo Sprint 3).`  
→ Sau demo, rerun pipeline chuẩn (không flag) → tất cả expectations OK, prune chunk stale từ index.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

> Bắt buộc: inject corruption (Sprint 3) — mô tả + dẫn `artifacts/eval/…` hoặc log.

**Kịch bản inject:**

Dùng `--no-refund-fix --skip-validate` để embed chunk refund stale (14 ngày thay vì 7 ngày) vào Chroma. Pipeline ghi nhận `embed_prune_removed=1` (xoá chunk clean cũ) và upsert 6 chunk inject (bao gồm chunk "14 ngày làm việc kể từ xác nhận đơn").

**Kết quả định lượng (từ CSV / bảng):**

| Câu hỏi | Metric | Inject (`after_inject_bad.csv`) | Clean (`after_clean_eval.csv`) |
|---------|--------|--------------------------------|-------------------------------|
| `q_refund_window` | `contains_expected` | yes | yes |
| `q_refund_window` | `hits_forbidden` | **yes** ⚠️ | **no** ✅ |
| `q_refund_window` | `top1_preview` | "...14 ngày làm việc..." | "...7 ngày làm việc..." |
| `q_leave_version` | `contains_expected` | yes | yes |
| `q_leave_version` | `hits_forbidden` | no | no |
| `q_leave_version` | `top1_doc_expected` | yes | yes |
| `q_p1_sla` | `contains_expected` | yes | yes |
| `q_lockout` | `contains_expected` | yes | yes |

**Nhận xét:** Inject chỉ ảnh hưởng câu `q_refund_window` — top-k chứa forbidden content "14 ngày làm việc". Sau khi rerun pipeline chuẩn, chunk stale bị prune và thay bằng chunk fix "7 ngày" → `hits_forbidden=no`. Câu `q_leave_version` không bị ảnh hưởng vì bản HR cũ (2025) luôn bị quarantine bởi baseline rule `stale_hr_policy_effective_date`.

---

## 4. Freshness & monitoring (100–150 từ)

> SLA bạn chọn, ý nghĩa PASS/WARN/FAIL trên manifest mẫu.

- **SLA:** `FRESHNESS_SLA_HOURS=24` — data snapshot không nên cũ hơn 24 giờ kể từ thời điểm export.
- **Kết quả manifest `clean-final`:**
  - `freshness_check=FAIL` — `age_hours≈120h` > SLA 24h → FAIL. Đây là hợp lý vì CSV mẫu có `exported_at=2026-04-10T08:00:00` (5 ngày trước).
  - `ingest_publish_lag=WARN` — lag≈120h > warn threshold 12h → pipeline chạy rất muộn so với export.
- **Ý nghĩa:** FAIL = cần re-export data mới từ nguồn. WARN = pipeline cần schedule thường xuyên hơn. PASS = data fresh, agent tin tưởng được.
- **Trong production:** Cron job chạy pipeline hàng ngày + alert Slack khi FAIL → giảm risk data stale.

---

## 5. Liên hệ Day 09 (50–100 từ)

> Dữ liệu sau embed có phục vụ lại multi-agent Day 09 không? Nếu có, mô tả tích hợp; nếu không, giải thích vì sao tách collection.

Dữ liệu embed vào collection `day10_kb` (tách riêng khỏi Day 09 `day09_kb`). Lý do: Day 10 xử lý **export CSV đã qua pipeline cleaning** (validate, fix refund, prune stale), trong khi Day 09 embed trực tiếp file `.txt`. Nếu tích hợp, agent Day 09 có thể đổi `CHROMA_COLLECTION=day10_kb` để dùng data đã validated — đảm bảo không trả lời sai do chunk stale.

---

## 6. Rủi ro còn lại & việc chưa làm

- Chưa tích hợp Great Expectations / pydantic model validation (dùng custom expectations).
- HR cutoff date hard-code `2026-01-01` — nên đọc từ contract YAML hoặc env.
- Freshness alert chưa tích hợp Slack/email thực tế.
- Chưa có multi-source ingestion (DB, API) — chỉ 1 file CSV.
- Chưa có LLM-judge eval — chỉ keyword-based retrieval check.
- Chưa có CI/CD pipeline tự động chạy ETL khi source thay đổi.
