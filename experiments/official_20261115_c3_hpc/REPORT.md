# C3 trên HPC-UIT (2026-11-15/16): seed gpt-oss-120b dưới 4 regime truy xuất

Lõi B / C3 của `SPEC_dong_gop_va_giao_thuc_so_sanh_2026-11-12.md`. Câu hỏi đo: (1) seed do LLM sinh có giúp tìm exploit hợp lệ nhanh hơn seed ngẫu nhiên không, và (2) lợi ích đó (nếu có) có đến từ rò rỉ hay không — rò rỉ qua truy xuất (regime `known` cho phép truy xuất bản ghi của chính sự cố đích) hoặc qua tiền huấn luyện (PolyNetwork 2021 nằm trước cutoff 06/2024 của gpt-oss-120b; bốn sự cố còn lại nằm sau).

Đây là **HPC run** (không phải chạy cục bộ trên laptop).

## Môi trường

| | Job 42012 (bản lỗi) | Job 42013 (bản vá) |
|---|---|---|
| Slurm | `account=uit`, `partition=normal`, `qos=mig2-35`, 8 CPU, 16 GB, `time=07:00:00`, CPU-only (không `--gres`) | như bên trái |
| Node | `h200node02` | `h200node02` |
| Thời gian (giờ VN) | 2026-11-15 22:08:12 → 2026-11-16 02:58:35 (4:50:23) | 22:08:12 → 02:58:28 (4:50:16) |
| Kết thúc | `COMPLETED`, exit `0:0`, MaxRSS 80,5 MB | `COMPLETED`, exit `0:0`, MaxRSS 92,7 MB |
| Run | 400/400 rc=0, 0 lỗi, 0 fallback seed | 400/400 rc=0, 0 lỗi, 0 fallback seed |
| `.err` | rỗng | rỗng |

- Mã nguồn: thư mục `/datastore/dungtrt/bridgesentry/repo_c3_89c0dbe`, giải nén từ `git archive` commit **`89c0dbe`** (`run_info.txt` ghi commit đầy đủ). Từ `5a6536d` (A-1) tới `89c0dbe` không có thay đổi nào trong `src/module3_fuzzing`, spec/hợp đồng fixture, `run_official.sh`, `empty_rpc.py`, `aggregate_official.py`.
- Binary: `bridgesentry-fuzzer` musl tĩnh, sha256 `d9cf542ecf64263565833788d9bd1c7e8936de635e9c5377580dd7011aeba848` (cùng binary với A-1). solc 0.8.20 static.
- RPC rỗng (`empty_rpc.py`, cổng ngẫu nhiên mỗi job): thực thi fixture cục bộ, **không** fork mainnet.
- Seed fuzzing 1042, 2042, …, 20042 (20 seed); ngân sách 300 s/run; `BRIDGESENTRY_OFFICIAL_STRICT_SEEDS=1` (run seed LLM không được lặng lẽ chạy bằng seed ngẫu nhiên; `runs_seed_fallback` = 0 ở mọi cấu hình).
- Seed LLM: `benchmarks/<b>/official/llm_outputs/gpt-oss-or/<regime>/` ở `89c0dbe` — openai/gpt-oss-120b qua OpenRouter, temperature 0,3, top-k 5, truy xuất all-MiniLM-L6-v2 + FAISS (strict, không hash fallback), KB đã kiểm toán 50 bản ghi. Job chép từng bộ seed sang `benchmarks/<b>/.seed_gpt-oss-or_<jobid>_<regime>/` (fuzzer lấy thư mục cha của `atg.json` làm thư mục benchmark), kiểm `cmp` và ghi sha256 vào `<variant>/seed_staging.sha256`; provenance của 20 bộ seed ở `<variant>/seed_provenance/`.
- Baseline so sánh: seed ngẫu nhiên của `official_20261114_a1_hpc` (cùng binary, cùng seed 1042–20042, cùng 300 s, cùng node).

## Kết quả

### Bản vá (FPR)

**0/400** run có cảnh báo (5 sự cố × 4 regime × 20 seed). Cộng với A-1: **0/540** run bản vá có cảnh báo trên các sự cố này.

### Bản lỗi: số run có exploit hợp lệ / 20 và median TTVE (s)

| Sự cố | Random (A-1) | known | exact | temporal | no_rag |
|---|---|---|---|---|---|
| Ronin bridge (2024) | 20/20 · 0,0109 | 20/20 · 0,0013 | 20/20 · 0,0016 | 20/20 · 0,0014 | 20/20 · 0,0008 |
| CrossCurve (2026) | 20/20 · 0,192 | 20/20 · 0,279 | 20/20 · 0,618 | 20/20 · 0,403 | 20/20 · 0,398 |
| Verus (2026) | 20/20 · 1,06 | 20/20 · 0,335 | 20/20 · 1,24 | 20/20 · 0,523 | 20/20 · 0,171 |
| **FEG SmartBridge (2024)** | **16/20 · 72,3** | **10/20 · > 300** | 17/20 · 90,8 | 14/20 · 149,9 | 13/20 · 181,9 |
| **PolyNetwork (2021)** | **1/20 · > 300** | 1/20 · > 300 | 0/20 · > 300 | 0/20 · > 300 | 0/20 · > 300 |

Hành động LLM ánh xạ được sang hàm gọi được (`actions_resolved`), bản lỗi: known 20/62 · 42/64 · 31/60 · 43/53 · 17/57; exact 27/53 · 20/58 · 28/58 · 35/49 · 5/55; temporal 23/59 · 48/65 · 21/52 · 40/49 · 10/49; no_rag 21/60 · 46/58 · 15/55 · 41/53 · 14/58 (thứ tự: CrossCurve · FEG · PolyNetwork · Ronin · Verus).

### Kiểm định (`analysis/vs_random_a1/comparisons.csv`, `analysis/regime_contrasts/comparisons.csv`)

Log-rank trên TTVE (run không có exploit bị censored ở 300 s) và Fisher exact trên tỷ lệ run có exploit; hiệu chỉnh Holm trong từng họ khai báo trước: LLM(regime) so với random (20 phép so sánh), và exact/temporal/no_rag so với known (15 phép so sánh). Ngưỡng 0,05 sau Holm.

- **FEG SmartBridge** (sự cố khó, sau cutoff): không regime nào hơn random. `known` thấp nhất (10/20 so với 16/20; log-rank p = 0,017 chưa hiệu chỉnh, chậm hơn random; 0,22 sau Holm). `exact` tốt hơn `known` (17/20 so với 10/20; Fisher p = 0,041 chưa hiệu chỉnh, 0,61 sau Holm).
- **PolyNetwork** (khó, trước cutoff): không regime nào giải được quá 1/20, giống random.
- **Sau Holm, chỉ còn ý nghĩa:** Ronin 2024, LLM nhanh hơn random ở cả 4 regime (median ≈ 0,001 s so với 0,011 s); Verus `no_rag` nhanh hơn random (0,17 s so với 1,06 s; p Holm 0,022); Verus `exact` chậm hơn `known` (1,24 s so với 0,34 s; p Holm 0,030); Ronin exact/no_rag khác known ở mức dưới 1 ms. Ở ba sự cố dễ, mọi run đều thành công trong vài giây, nên các khác biệt này có ý nghĩa thống kê nhưng không có ý nghĩa thực tế (vài mili giây tới chưa tới 1 s).

## Cách đọc (trung thực)

1. **Đối chứng bản vá đứng vững với seed LLM:** 0/400 cảnh báo, tổng cộng 0/540 cùng A-1.
2. **Không có bằng chứng seed LLM giúp tìm exploit ở các sự cố khó.** Trên FEG và PolyNetwork, những nơi seed ngẫu nhiên chưa chạm trần, seed gpt-oss-120b không hơn random ở regime nào; trên FEG, regime `known` còn kém hơn random (không còn ý nghĩa sau Holm).
3. **Không có dấu hiệu rò rỉ làm phồng kết quả.** Cho phép truy xuất bản ghi của chính sự cố (`known`) không làm kết quả tốt hơn `exact`, `temporal` hay `no_rag`; trên FEG nó còn tệ nhất. Sự cố trước cutoff (PolyNetwork) cũng không được giải nhờ tri thức tiền huấn luyện. Nghĩa là trên các fixture này, rò rỉ không thổi phồng tỷ lệ tái dựng — nhưng cũng vì seed LLM không mang lại lợi thế nào để rò rỉ có thể thổi phồng.
4. Giới hạn: một model (gpt-oss-120b), 5 sự cố (2 sự cố khó), fixture là bản tái hiện tối giản, RPC rỗng; tỷ lệ ánh xạ hành động thấp ở một số bộ seed (Verus `exact` 5/55) có thể khiến seed LLM thực chất gần với seed ngẫu nhiên.

## Tệp

- `vulnerable/`, `patched/`: thư mục run gốc của HPC (`<regime>/official_runs/<bench>/<variant>/llm/seed_<n>.{json,log,rc}`, `summary_official.csv` do HPC sinh — đã đối chiếu sha256 8/8 với bản trên HPC, không chạy lại aggregate), `jobs.txt`, `run_info.txt`, `seed_staging.sha256`, `seed_provenance/`, `slurm_logs/c3_<job>.{out,err}`.
- `job_c3_llm.sh`: script job đã chạy (bản trong repo ở `89c0dbe`).
- `analysis/<variant>_<regime>/`: `analysis_ver_fpr.csv` (Clopper–Pearson 95%), `survival_steps.csv` (Kaplan–Meier), `logrank.csv` — từ `scripts/official/analyze_official.py`.
- `analysis/vs_random_a1/`: LLM(regime) so với random A-1 — `comparisons.csv` (Fisher, log-rank, Holm, chiều nhanh/chậm), cùng `logrank_<regime>.csv`, `ver_fpr_<regime>.csv`. Tính trên thư mục gộp tạm (bản sao run A-1 random + run C3 llm), không lưu bản sao run vào hồ sơ.
- `analysis/regime_contrasts/`: exact/temporal/no_rag so với known (cùng cách; run `known` được gán nhãn nhóm thứ hai — log-rank và Fisher đối xứng nên kết quả không phụ thuộc nhãn).

## Ghi chú vận hành

- Bản `vulnerable` tải lần đầu bằng `scp -r` bị đứt kết nối; tải lại dưới dạng một tarball, sha256 khớp hai đầu (`501eb38d…`), số file khớp (1227). File tạm `/datastore/dungtrt/bridgesentry/upload/c3_vuln_xfer.tgz` còn để lại trên HPC.
- Job không dọn 40 thư mục seed tạm `benchmarks/*/.seed_gpt-oss-or_<jobid>_<regime>/` trong `repo_c3_89c0dbe` (bản sao repo riêng của đợt này); vô hại, chưa xoá.
