# BridgeSentry — bảng tiến độ thực nghiệm

Theo dõi `docs/EXPERIMENT_PLAN.md` (Bước 0–10, Đ1–Đ8) và `todo.txt` (A1–A9, B1–B8, C1–C6).
Cập nhật ở mỗi mốc. Phân biệt bốn mức: **có code** / **đã test** / **đã nghiệm thu** / **có kết quả thực nghiệm**.

Cập nhật lần cuối: 2026-11-06 (HPC Bước 1 nghiệm thu).

## Quy tắc cố định (khoá cho mọi chiến dịch)
- Oracle: `BRIDGESENTRY_EVALUATION_MODE=official` (execution-only asset conservation); runner `scripts/official/`.
- Đơn vị thống kê: 1 run = 1 (fixture, variant, cấu hình seed, PRNG seed). VER tính ở đơn vị sự cố; Verus (surrogate) báo riêng.
- Exploit hợp lệ = qua đủ 7 cổng (`is_valid_exploit`): bytecode đích thực thi, đường nhân quả qua release/relay, đổi trạng thái, đúng capability (relay faithful), replay được, có tác động, bản vá chặn.
- RPC rỗng = thực thi fixture cục bộ, KHÔNG phải fork mainnet — luôn ghi rõ.
- Run lỗi (crash / thiếu JSON / cấu hình sai) KHÔNG tính là "hoàn tất không tìm thấy", KHÔNG censored; đếm ở `runs_failed`.
- Không bịa số; chưa có thì "—" + lý do. Không gộp backend LLM khác nhau. Job GPU phải xin phép người dùng.

## Bước 0–10

| Bước | Trạng thái | Bằng chứng / commit | Còn thiếu |
|---|---|---|---|
| 0. Đồng bộ, khoá quy trình | đang làm | file này (`980a542`) | — |
| 1. Môi trường HPC | **ĐÃ NGHIỆM THU** | job CPU-only 10714 trên h200node02 (normal/mig2-35, no GPU); binary musl static sha256 `8d2c004a…`; hồi quy Nomad/Qubit 5/5 lỗi, 0/5 vá, 0 fail — `experiments/official_20261106_hpc_regression/` | — |
| 2. Nghiệm thu fixture + Đ1 | **một phần** | 7 fixture có test xác định; Đ1 phần (b) đạt: test qua đủ 7 cổng (`980a542`) | Đ1 phần (a) — search có tới được Seq không — xem mục fixture dưới; 2 quyết định chờ người dùng |
| 3. KB + đối chứng âm | **một phần** | `docs/kb_audit.md` (nháp) | chuẩn hoá snapshot KB + hash; 2 bridge benign chưa viết |
| 4. Holdout + runner | **một phần** | runner đã sửa (strict seeds, mã thoát, `runs_failed`) `de75daa`; test runner 6 pass | 4 chế độ holdout + no_rag chưa implement; chưa có bộ lọc KB |
| 5. Sinh Module 1–2, chi phí | **chờ key** | model chốt: gpt-oss-120b (chính) + **OpenAI GPT-5-class (frontier, phương án A)**; key qua `C:\Users\Admin\.bridgesentry.env` (ngoài repo) | user tạo file key; rồi dựng venv, sinh seed 7 fixture official + probe ghi nhớ |
| 6. Pilot + ma trận chính | **một phần** | `experiments/official_20261105_local_pilot/g20` (4 fixture dễ, 60 run, 0 lỗi; `980a542`) | nhóm 3 fixture khó (pilot 120s/600s) bị dừng do thiếu RAM; ma trận chính trên HPC |
| 7. Thống kê | **chưa** | — | script `analyze_official.py` (KM, log-rank, Fisher, Holm, bootstrap) |
| 8. Baseline A1 | **chưa** | — | kiểm tra artifact BridgeFuzz/ItyFuzz |
| 9. Rollback/reorg A6 | **chưa** | — | thiết kế 2 kịch bản + mở rộng harness có test |
| 10. Paper song song | **chưa** | — | Table 2 phân loại mới, số KB sau chuẩn hoá, Setup |

## todo.txt

| Mục | Trạng thái | Ghi chú |
|---|---|---|
| A1 BridgeFuzz/ItyFuzz | chưa | Bước 8 |
| A2 bản vá | một phần | Nomad/Qubit có kết quả; 5 fixture mới có test xác định qua 7 cổng; chờ kết quả search |
| A3 benign/hard negative | một phần | hard negative = bản vá; benign chưa viết |
| A4 holdout | chưa | Bước 4–5 |
| A5 parser-only | chưa | Bước 5 |
| A6 reorg | chưa | Bước 9 |
| A7 phân phối thời gian | một phần | TTVE median/max + censored có trong aggregate; cần 20 seed + survival |
| A8 token/latency | chưa | Bước 5 |
| A9 inter-rater | không áp dụng | số 66,3% đã rút; ghi một câu trong paper |
| B1 | xong | đường đi Module 1–2 vào fuzzer đã rõ |
| B2 | xong | distance legacy không đưa vào paper |
| B3 | xong | w(s) đã sửa đúng code trong `main.tex` |
| B4 | xong | 20 seed = chiến dịch legacy |
| B5 | chờ người dùng | số core; sẽ lấy từ manifest HPC |
| B6 | chờ người dùng | ngày Orbit (metadata vs paper) |
| B7 | một phần | model: gpt-oss-120b chính + 1 frontier; seed thật chưa sinh |
| B8 | xong | official báo PC duy nhất, không dùng basic-block legacy |
| C1 artifact/DOI | một phần | repo public; DOI Zenodo chưa |
| C2 funding | xong | giữ "no specific grant" + Acknowledgements UIT (`main_bcra.tex`) |
| C3 thay preprint | chưa | khi bản xuất bản xuất hiện |
| C4 hình vector | chưa | Module 1 không có nguồn draw.io (Đ8) |
| C5 Figure 5 | không áp dụng | đã bỏ theo hướng (a) |
| C6 ORCID footer | một phần | đã xử lý trong `main_bcra.tex` |

## Trạng thái 7 fixture (nhóm A)

| Fixture | Test xác định (7 cổng, Đ1-b) | Search random tìm ra (smoke) | Seed LLM thật | Ghi chú |
|---|---|---|---|---|
| nomad | đạt | có (đợt official) | có (18 scenario) | bão hoà |
| qubit | đạt | có | có (20 scenario) | bão hoà |
| ronin_2024 | đạt | có (≈0,0006 s) | placeholder → chỉ random | bão hoà; sau cutoff gpt-oss |
| verus | đạt | có (≈0,36 s) | placeholder | surrogate non-EVM; sau cutoff |
| feg_bridge_2024 | đạt | **chưa** (0/3 @120s) | placeholder | sau cutoff; cần seed LLM thật + có thể mở rộng mutator |
| crosscurve | đạt | **chưa** (0/3 @120s) | placeholder | sau cutoff; như trên |
| polynetwork | đạt | **chưa** (0/3 @120s) | placeholder | trước cutoff; keeper mô hình bằng address (mất va chạm selector) |

**Phát hiện Đ1:** cả 7 fixture đều biểu diễn được exploit dưới dạng Seq qua đủ 7 cổng oracle (phần b).
Nhưng với 3 fixture khó (FEG, CrossCurve, PolyNetwork), search ngẫu nhiên chưa sinh ra được Seq đó (phần a).
→ Cần quyết định: (1) mở rộng không gian hành động/mutator để search tới được (có test, mô tả trong paper),
hay (2) ghi 3 fixture này là "chỉ biểu diễn được, search chưa tới". Chờ người dùng.

## Quyết định đang chờ người dùng
1. PolyNetwork: giữ mô hình keeper = address (mất va chạm selector) hay dựng lại cho sát sự cố.
2. Mở rộng mutator cho 3 fixture khó, hay ghi "search chưa tới".
3. Chốt model frontier + cấp API key (`NVIDIA_API_KEY` + key frontier) cho Bước 5.
4. HPC: bật VPN để chạy Bước 1 (hoặc để người dùng tự submit).
