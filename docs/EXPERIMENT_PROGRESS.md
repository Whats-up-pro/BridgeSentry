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

## Phát hiện 2026-11-07: patched-control chưa sạch cho CrossCurve/PolyNetwork

Mutator mở rộng (commit `a90aa3d`) khi chạy 600 s random lộ ra: bản **vá** của CrossCurve và PolyNetwork
vẫn cho candidate lợi nhuận dương (`runs_with_any_alert`=5/5), dù `valid_exploits=0`. Chi tiết + số liệu:
`experiments/official_20261106_hard_before_after/`.

Root cause (đã truy): **không** phải `OfficialToken.setMinter` (có kiểm owner, call revert) và **không** phải
tự-attest ở gateway (`approveContractCall` có kiểm relayer). Lợi nhuận đến qua **đường relay** (`@dest:Relay`):
kẻ tấn công gọi `AxelarGateway.callContract` ở chain nguồn với payload trả cho mình → relayer **trung thực**
attest + execute ở chain đích → `ReceiverAxelar.execute` trả tiền, vì fixture **cố ý bỏ kiểm `sourceAddress`**
(tác giả fixture cho là "useless"). Hệ quả: đích thực thi mọi thông điệp đã-attest, kể cả thông điệp kẻ tấn công
tự phát từ nguồn → bản vá không chặn đường này.

**Tại sao VER bản lỗi vẫn đúng:** exploit "valid" của bản lỗi đi qua `expressExecute` (bỏ qua gateway) và **bị
`patched_rejected` loại** khi chạy trên bản vá → nên 5/5 valid của crosscurve vulnerable là đường tài liệu thật,
không phải đường relay này. Đường relay cho lợi nhuận trên CẢ hai biến thể nên không bao giờ thành "valid".

**Quyết định cần người dùng (mô hình hoá, KHÔNG tự sửa để tránh làm sai lệch):**
- Có mô hình hoá ràng buộc `sourceAddress` (đích chỉ thực thi thông điệp phát từ PortalSrc hợp lệ, như Axelar thật
  ràng buộc nguồn qua lệnh đã-attest) để bản vá sạch không? Nếu có, cả vulnerable lẫn patched phải ràng buộc nguồn,
  và exploit tài liệu vẫn phải khai thác được trên vulnerable.
- Hay giữ mô hình hiện tại và **không báo patched-control/FPR** cho crosscurve/polynetwork, chỉ báo VER bản lỗi?
- Kiểm tra polynetwork tương tự (alert qua đường nào) trước khi quyết.

FEG patched sạch (0 alert) nên không vướng.


## 2026-11-08: hạ tầng sinh seed (holdout) + phân tích thống kê (Bước 4 + Bước 6)

Đã commit lên `main` và kiểm thử:
- `1401ef4` — **seed generator** `scripts/official/generate_seeds.py`: chạy Module 1 (ATG+invariant) + Module 2
  (scenario) cho một fixture official theo (backend LLM × regime holdout); ghi `atg.json`/`hypotheses.json`/
  `provenance.json` + cost ledger. Ép đúng 1 backend/lần (gỡ key provider kia trước khi resolve → không trộn),
  đếm token/latency thật (A8), đánh dấu từng scenario `llm` vs `deterministic_fallback` (fallback không bị tính là
  LLM), tách `--parser-only` (A5: Module 1 không LLM, Module 2 vẫn LLM).
  - `src/module2_rag/holdout.py` — lọc regime `known/no_rag/exact/family/temporal`, registry sự cố + alias (gồm
    bản `*_xscope`), ghi id bị loại vào provenance. 9 unit test (`tests/test_holdout.py`).
  - `src/common/llm_client.py` — tham số theo họ model: model reasoning OpenAI (o1/o3/o4, gpt-5+/gpt-6+, vd gpt-5.5)
    bỏ `temperature`, dùng `max_completion_tokens`; nhận diện trên tên model trần nên gpt-oss (có prefix provider)
    không bị ảnh hưởng. **Đã xác nhận với API gpt-5.5 thật** (trả `{"ok":true}`).
  - 4 record KB cho sự cố nhóm A sau 2022 (`ronin_20240806`, `feg_bridge_20241229`, `crosscurve_20260131`,
    `verus_20260518`), **lấy nguyên từ metadata.json đã kiểm nguồn trong repo** → regime `known`/`temporal` mới có
    nghĩa cho 4 fixture này. KB 48→52; test schema cũ vẫn pass.
- `b8d29db` — **phân tích thống kê** `scripts/official/analyze_official.py` (A7): VER/FPR + CI Clopper–Pearson 95%,
  survival Kaplan–Meier (completed không có exploit = censored tại budget), log-rank llm-vs-random. Không phụ thuộc
  scipy/matplotlib (CP + đuôi chi-square tự cài). `--selftest` pass; chạy trên `experiments/official_20261103/
  official_runs` **tái lập đúng** summary cũ (nomad/qubit vulnerable 5/5, patched 0/5, median TTVE khớp), thêm
  CI + p-value.
- `180cfff` — `run_matrix.sh`/`run_official.sh`: `SEED_SUBDIR` + positional `seed_dir` để mỗi (model×regime) chạy
  như một pass riêng, trỏ tới seed đã sinh ở `benchmarks/<b>/official/llm_outputs/<model>/<regime>`. Mặc định không
  đổi.

### Chốt chặn hiện tại (CẦN NGƯỜI DÙNG) — token cho gpt-oss-120b
Smoke sinh seed nomad chạy đúng toàn bộ pipeline, nhưng **Groq free tier giới hạn gpt-oss-120b = 200.000 token/ngày**
và đã cạn (`Used ~199.787/200.000`) → phần lớn call 429, seed rơi về template fallback (ghi trung thực `n_llm=0`,
không giả làm LLM). gpt-oss là model **chính** (cutoff 06/2024 sạch), nên chiến dịch (6 fixture × 4 regime +
parser-only ≈ 1–2M token) **không chạy được** trên free tier.
- Đề xuất: nâng Groq lên **Dev tier** (trả theo dùng, ~vài USD cho cả chiến dịch) tại
  `console.groq.com/settings/billing`. Hoặc đổi host gpt-oss-120b (Fireworks/Together/DeepInfra).
- gpt-5.5 (frontier) KHÔNG bị cap này, đã chạy được; **đang giữ** chưa sinh seed frontier để sinh cùng lúc với
  gpt-oss (so sánh công bằng) và chốt chi phí với người dùng trước.


## 2026-11-08: hằng số lấy từ test exploit nằm trong từ vựng mutator (CẦN SỬA trước chiến dịch chính)

Phát hiện khi viết đoạn mô tả mutator cho paper (rà `official_mode.rs` ở `main`):
- `Dict::from_world` (thêm ở `a90aa3d`) đưa hằng `parse_uint("500000e18")` vào danh sách `amounts`.
- `500000e18` **chính là số tiền rút** trong các test exploit viết tay của 5 fixture: `feg_bridge_2024`, `crosscurve`,
  `ronin_2024`, `polynetwork`, `verus` (các test `*_official_exploit_and_patch` trong `mod fixture_tests`).
  Nó không phải thanh khoản nạp sẵn (thanh khoản là `1000000e18`, xem `setup` trong `spec.json`).
- Như vậy giá trị lấy từ exploit đã biết bị đưa vào không gian tìm kiếm. Điều này vi phạm quy tắc
  "toán tử mới phải tổng quát, không viết riêng cho exploit của một fixture" (quyết định 06/11, mục 2).
  Câu "It encodes no fixture-specific exploit" trong doc comment của `Dict` hiện chưa đúng.

Mức ảnh hưởng **chưa đo**. Oracle chỉ cần lợi nhuận ròng > 0, nên mọi số dương ≤ thanh khoản đều có thể
cho exploit (từ vựng còn có 1e18, 1e21, 1e23, 1e24). Vì vậy hằng này có thể không quyết định kết quả, nhưng phải chứng minh bằng số liệu:
1. Bỏ `500000e18` khỏi `Dict::from_world`. Nếu cần số lớn thì lấy từ trạng thái fixture (ví dụ đọc số dư token
   của các hợp đồng đã deploy sau `setup`), áp dụng như nhau cho mọi fixture. Thêm test khẳng định từ vựng không chứa
   số tiền của các test exploit.
2. Chạy lại before/after 3 fixture khó (cùng cấu hình `experiments/official_20261106_hard_before_after/`: random,
   5 seed, 600 s) vào **thư mục mới**. Không sửa thư mục cũ (hồ sơ đóng băng).
3. Chạy lại 4 fixture dễ để chắc kết luận không đổi.
4. Kết quả before/after ngày 06/11 (CrossCurve 5/5, FEG 4/5, PolyNetwork 1/5) chỉ được trích sau khi có số của bản
   đã bỏ hằng. Nếu hai bản khác nhau, báo cả hai.

Ghi chú phụ (không chặn): các luỹ thừa 10 cố định (1e18, 1e21, 1e23, 1e24) là giá trị biên chung, không lấy từ test.
Tuy nhiên 1e24 trùng thanh khoản nạp sẵn của 5 fixture, và 1e18, 1e21, 1e24 đã có trong `mutate_token_raw` từ trước `a90aa3d` (1e23 mới thêm ở `a90aa3d`).
Paper (`main.tex`, `main_bcra.tex`, mục Evaluated configuration) đã mô tả từ vựng là "small integers and boundary amounts"
kèm `% TODO(authors)`; sửa câu đó theo bản code cuối.


## 2026-11-13: A-0 ĐÓNG (cổng chặn chung) + A-1 sẵn sàng cho HPC

### A-0 hoàn tất, đã verify (local WSL, KHÔNG phải HPC)
- **pt1 `56d5fc1`:** gỡ hằng `500000e18` khỏi `Dict::from_world` + test no-leak. `cargo test` 189+170 xanh.
- **pt2 CrossCurve `13d9817`:** gateway attest source (`approveContractCall(commandId, source)` /
  `validateContractCall(commandId, expectedSource)`), `ReceiverAxelar` bind `sourceAddress == trustedSource`
  (relay truyền `ev:sender`); khác biệt vuln/patched vẫn là gateway-validation ở `expressExecute`.
  Verify (random × 60s): vulnerable 3/3 valid (median 0.6s), **patched 5/5 → 0/3 alert**.
  `experiments/official_20261113_crosscurve_sourceaddr_after/`.
- **pt2 PolyNetwork `1149b42`:** lỗ KHÁC crosscurve — manager append `fromContract` sau `args` attacker
  (args-injection, không phải sourceAddress). Sửa: manager giữ `fromContractContext()` (nguồn tin cậy),
  `LockProxy.unlock(address,uint256)` đọc context thay vì args; `putCurEpochConPubKeyBytes(address)`.
  Verify: **patched 3/3 → 0/3 alert**; vulnerable 2/3 → 0/3 (shortcut giả biến mất, còn exploit 2-bước tài liệu
  mà random 60s không với tới — đúng chỗ seed LLM/C3 phải chứng tỏ). `experiments/official_20261113_polynetwork_fromcontext_after/`.
- **Paper:** gỡ 2 TODO đã giải quyết trong `main.tex`+`main_bcra.tex` (mutator leak; PolyNetwork abstraction theo
  QĐ2 = giữ abstraction + câu mô tả đã có).
- **Trung thực (gap-first):** không nới oracle/mutator để che alert; chỉ tăng độ trung thực fixture (mô hình đúng
  ràng buộc nguồn mà cầu nối thật enforce). ⇒ **CrossCurve + PolyNetwork giờ là patched-control C1 hợp lệ** (trước
  chỉ Nomad/Qubit).

### A-1 sẵn sàng (Lõi A = C1 FPR + C2 VER, không cần token LLM)
- Binary **musl `d9cf542e…`** (commit `1149b42`, static-pie); smoke Nomad OK (vuln 1/1, patched 0/0).
- Job HPC **`ed5f6cc`** `scripts/official/job_a1_random.sh`: PDF-compliant (account=uit, partition=normal,
  qos=mig2-35, **no --gres**, 16 cpu, 4h), 280 run (7 fixture × {vuln,patched} × 20 seed × 300s) gom 1 job `xargs -P 14`.
- **Blocker HPC:** SSH key mất khỏi `%TEMP%` (Connect-Hpc.ps1 trỏ path đã bị dọn) → chờ người dùng khôi phục từ
  `.ppk` thầy cấp. VPN đang bật (TCP cổng 22 reachable). Luồng khi có key: scp binary → cập nhật repo HPC lên
  `ed5f6cc` → `sbatch` → đọc `.out/.err` → chép về `experiments/` → báo người dùng (theo PDF).
- Pilot A-1 **local** (7 fixture × {vuln,patched} × 3 seed × 120s) đang chạy lấy số sơ bộ trong lúc chờ key.
