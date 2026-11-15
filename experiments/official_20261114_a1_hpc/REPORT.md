# A-1 trên HPC-UIT (2026-11-14): 7 fixture on-chain × {lỗi, vá} × seed ngẫu nhiên

Lõi A của `SPEC_dong_gop_va_giao_thuc_so_sanh_2026-11-12.md`: đo **VER** (tỷ lệ run có exploit hợp lệ trên bản lỗi) và **FPR** (tỷ lệ run có cảnh báo trên bản vá) cho cả 7 sự cố on-chain, bằng seed **ngẫu nhiên**, oracle official. Đây là baseline random mà chiến dịch seed LLM (C3) sẽ so sánh với, cùng binary, cùng seed, cùng ngân sách.

Đây là **HPC run** (không phải chạy cục bộ trên laptop).

## Môi trường

- Slurm job **30578**, node `h200node02`. Job CPU-only (không `--gres`): `account=uit`, `partition=normal`, `qos=mig2-35`, `cpus-per-task=8`, `mem=16G`, `time=04:00:00`. Chạy 2026-11-14 12:05:47 → 15:26:04 (3:20:17), `COMPLETED`, exit `0:0`, MaxRSS 77 MB. 280 run gom trong một job bằng `xargs -P 7`, theo `Huong_dan_HPC_dungtrt.pdf`.
- Mã nguồn: repo trên HPC là `git archive` của commit **`5a6536d`** (đã đọc commit id nhúng trong tarball). `scripts/official/job_a1_random.sh` là bản 8 CPU, sha256 khớp với bản đã commit ở `ceb204f`. `run_official.sh` khớp `5a6536d`. Bản sao của script job: `slurm_logs/job_a1_random.sh`.
- Binary: `bridgesentry-fuzzer` musl tĩnh, sha256 `d9cf542ecf64263565833788d9bd1c7e8936de635e9c5377580dd7011aeba848`, build ở `927097e`. Từ `1149b42` (A-0 xong) tới `5a6536d` không có thay đổi nào trong `src/module3_fuzzing` hay trong spec/hợp đồng fixture.
- solc 0.8.20 static, sha256 `0479d44fdf9c501c25337fdc540419f1593b884a87b47f023da4f1c700fda782`; python3 3.12 của cụm.
- RPC rỗng (`empty_rpc.py`): thực thi fixture cục bộ, **không** fork mainnet.
- Seed 1042, 2042, …, 20042 (20 seed); ngân sách 300 s/run; `BRIDGESENTRY_OFFICIAL_STRICT_SEEDS=0` (chỉ có ý nghĩa với seed LLM; ở đây toàn bộ là random).

## Kết quả

280/280 run hoàn tất, rc=0, **0 run lỗi, 0 fallback seed**. Khoảng tin cậy 95% Clopper–Pearson, tính bằng `scripts/official/analyze_official.py` (`analysis/analysis_ver_fpr.csv`). Số liệu thô: `official_runs/summary_official.csv` (bản gốc do HPC sinh, sha256 `9a359d02…`).

| Sự cố | VER bản lỗi | CI 95% | Median TTVE (s) | Max TTVE (s) | FPR bản vá | CI 95% |
|---|---|---|---|---|---|---|
| Nomad | 20/20 | [0,83; 1,00] | 0,0022 | 0,0071 | 0/20 | [0; 0,17] |
| Qubit | 20/20 | [0,83; 1,00] | 0,176 | 0,846 | 0/20 | [0; 0,17] |
| PolyNetwork | **1/20** | [0,001; 0,25] | > 300 | 246,9 | 0/20 | [0; 0,17] |
| Ronin bridge (2024) | 20/20 | [0,83; 1,00] | 0,0109 | 0,131 | 0/20 | [0; 0,17] |
| FEG SmartBridge | **16/20** | [0,56; 0,94] | 72,3 | 253,0 | 0/20 | [0; 0,17] |
| CrossCurve | 20/20 | [0,83; 1,00] | 0,192 | 1,13 | 0/20 | [0; 0,17] |
| Verus (surrogate) | 20/20 | [0,83; 1,00] | 1,06 | 12,3 | 0/20 | [0; 0,17] |

- Gộp 7 bản vá: **0/140** run có cảnh báo, CI 95% [0; 0,026].
- Trên bản lỗi, mọi run có cảnh báo đều là exploit hợp lệ (`runs_with_any_alert = runs_with_valid_exploit` ở cả 7 fixture).
- TTVE là thời gian fuzzing tới exploit hợp lệ đầu tiên; run không tìm ra bị censored tại 300 s (`analysis/survival_steps.csv`). `analysis/logrank.csv` trống vì đợt này không có seed LLM để so.

## Cách đọc

- **C1 (đối chứng bản vá):** mở rộng từ 2 lên 7 sự cố. Trên cả 7, bản vá không có cảnh báo nào trong 140 run × 300 s, dù mỗi run thực thi khoảng 380.000–740.000 iteration.
- **Độ khó của fixture với seed ngẫu nhiên:** 5/7 sự cố (Nomad, Qubit, Ronin 2024, CrossCurve, Verus) bị random tìm ra trong vài giây, nên **không** dùng được để chứng minh lợi ích của seed LLM. Hai sự cố khó là **FEG SmartBridge** (16/20, median 72 s) và **PolyNetwork** (1/20). Đây là chỗ RQ3 có thể phân biệt được seed LLM với random.
- **C2/RQ2:** random đã tìm ra exploit trên cả bốn sự cố mà exploit phải đi từ chuỗi nguồn qua relay (Qubit, PolyNetwork, FEG, Verus). Điều này cho thấy harness hai chuỗi tái dựng được đường đi qua relay. Nó chưa phải so sánh với fuzzer đơn chuỗi; ItyFuzz và BridgeFuzz chưa chạy.
- Nomad và Qubit khớp ba round trước (5 seed × 20 s): bản lỗi 100%, bản vá 0%.

## Tệp

- `official_runs/<bench>/<variant>/random/seed_<n>.{json,log,rc}`: kết quả từng run; `official_runs/jobs.txt`: danh sách 280 run; `official_runs/summary_official.csv`: tổng hợp do HPC sinh.
- `analysis/`: `analysis_ver_fpr.csv`, `survival_steps.csv`, `logrank.csv` (tính lại ở máy local từ cùng dữ liệu).
- `slurm_logs/a1_30578.out` (stdout), `a1_30578.err` (rỗng), `job_a1_random.sh`.
