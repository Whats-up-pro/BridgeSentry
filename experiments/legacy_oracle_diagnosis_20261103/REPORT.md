# Chạy lại BridgeSentry với dữ liệu LLM thật (3/11/2026)

## Kết luận

Kết quả 12/12 benchmark trigger **không phụ thuộc vào việc bytecode có chạy hay không**. Oracle hiện tại (legacy) tính vi phạm invariant hoàn toàn từ **nội dung văn bản scenario do LLM sinh ra**, nên:

- Không chạy bytecode nào: vẫn trigger 12/12.
- Chạy bytecode thật nhưng checker chỉ thấy trạng thái thực thi: **0/11 trigger**.
- Vá lỗi gốc của Nomad: **vẫn trigger 3/3 seed, đủ 18/18 invariant**.

Cho nên mọi thí nghiệm mới (holdout, patched control, chạy 200 job trên HPC) chạy với oracle legacy sẽ cho kết quả không có ý nghĩa. Phải nối đường đánh giá "official" (task A1.2) trước.

## Thiết lập

- **Code:** `Whats-up-pro/BridgeSentry`, commit `db20af7` (9/10/2026), fuzzer build release (Rust 1.97).
- **Đầu vào:** output LLM thật đã commit trong repo, `benchmarks/<bridge>/llm_outputs/{atg,hypotheses}.json` (gpt-oss-120b, sinh tháng 4/2026). Không gọi lại LLM.
- **Thực thi:** dual-EVM (revm) với hợp đồng fixture trong `benchmarks/<bridge>/contracts/`, do fuzzer tự compile (solc 0.8.20) và deploy.
  - Thay cho RPC mainnet là một RPC giả trả trạng thái rỗng (`empty_rpc.py`), vì môi trường cloud không gọi được RPC bên ngoài.
  - Đây là **thực thi fixture cục bộ, không phải fork mainnet**.
- **Ngân sách:** 20 giây/run, 3 seed (1042, 2042, 3042), α=0.3, β=0.4, γ=0.3. Paper dùng 600 giây × 20 run, nhưng trigger luôn xảy ra trong vài mili giây đầu nên ngân sách ngắn không ảnh hưởng kết luận.

| Điều kiện | Ý nghĩa |
|---|---|
| `syn` | Không có RPC, fuzzer tự rơi về chế độ chỉ dùng trạng thái suy ra từ scenario (0 bytecode) |
| `real` | Có dual-EVM + fixture bytecode, oracle legacy (đúng như sweep "realbytecode" của paper) |
| `exec` | Như `real`, nhưng bỏ mọi dữ kiện suy ra từ văn bản scenario (cờ chẩn đoán `BRIDGESENTRY_DIAG_EXEC_ONLY=1`) |
| `nomad_patched` | Fixture Nomad đã vá: `acceptableRoot` từ chối root `0x00` |

## Kết quả (median trên 3 seed)

| Benchmark | syn: trigger / invariant / BB | real: trigger / invariant / BB nguồn–đích | exec: trigger / BB nguồn–đích |
|---|---|---|---|
| nomad | 3/3 · 18/18 · 0 | 3/3 · 18/18 · 239–196 | **0/3** · 242–199 |
| qubit | 3/3 · 20/20 · 0 | 3/3 · 20/20 · 534–0 | **0/3** · 534–0 |
| pgala | 3/3 · 19/19 · 0 | 3/3 · 19/19 · 373–0 | **0/3** · 373–0 |
| polynetwork | 3/3 · 16/16 · 0 | 2/3 · 16/16 · **0–0** | **0/3** · 0–0 |
| wormhole | 3/3 · 19/19 · 0 | lỗi deploy (`TokenBridge CREATE address mismatch`) | lỗi deploy |
| socket | 3/3 · 19/19 · 0 | 3/3 · 19/19 · 688–688 | **0/3** · 654–654 |
| ronin | 3/3 · 20/20 · 0 | 3/3 · 20/20 · 485–0 | **0/3** · 464–0 |
| harmony | 3/3 · 19/19 · 0 | 3/3 · 19/19 · 470–0 | **0/3** · 470–0 |
| multichain | 3/3 · 21/21 · 0 | 3/3 · 21/21 · 652–0 | **0/3** · 629–0 |
| orbit | 3/3 · 18/18 · 0 | 3/3 · 18/18 · 259–0 | **0/3** · 449–0 |
| fegtoken | 3/3 · 20/20 · 0 | 3/3 · 20/20 · 223–0 | **0/3** · 209–0 |
| gempad | 3/3 · 20/20 · 0 | 3/3 · 20/20 · 551–0 | **0/3** · 714–0 |
| **nomad_patched** | — | **3/3 · 18/18** · 239–239 | **0/3** · 305–305 |

BB = số basic block thực thi. "Invariant" = số invariant khác nhau bị báo vi phạm / tổng số invariant LLM sinh ra.

Thời gian đến trigger đầu tiên (`real`, 32 run có trigger): median **0,0024 s**, max 0,11 s. Tức là các scenario LLM *ban đầu* đã "vi phạm" ngay vòng đầu, trước khi fuzzing kịp làm gì.

## Năm phát hiện

1. **Oracle đọc văn bản, không đọc thực thi.** `fuzz_loop.rs:289` dựng trạng thái cho checker bằng `scenario_sim::global_state_from_scenario`. Hàm này cộng các con số `amount` trong scenario thành `__locked__`/`__minted__`. Checker chỉ đọc hai khóa này (và cờ `zero_root_accepted`, cũng suy ra từ văn bản). Số dư on-chain có được ghép vào state, nhưng checker không đọc tới.
   - Ví dụ: Nomad, scenario `nomad_nonce_reorder_001`. Từ các số trong văn bản (đã qua mutation), oracle tính locked = 1000e18 và minted = 2000e18, rồi báo `asset_conservation_total` vi phạm ở 0,0025 s.
   - JSON output của chính fuzzer cũng tự ghi `official_eligible: false, oracle_state_source: mixed`.
2. **229 invariant LLM chỉ quy về 3 hàm kiểm tra.** Checker chọn hàm theo `category`: conservation, authorization, uniqueness. Cả ba đều chủ yếu kiểm `minted > locked`. Không invariant nào có `"root"` trong ID nên hàm `check_root_validation` không bao giờ được gọi. Hệ quả là một scenario "mint nhiều hơn lock" làm *mọi* invariant cùng loại vi phạm cùng lúc (18/18, 20/20…). Con số "invariant bị vi phạm" trong paper vì vậy không mang thông tin.
3. **Bản vá không làm thay đổi kết quả.** Nomad đã vá vẫn cho 3/3 trigger và 18/18 invariant. Oracle hiện tại không thể đáp ứng tiêu chí "patched control" mà reviewer đòi.
4. **Phần lớn benchmark không chạy bytecode ở chain đích.** 9/11 benchmark chạy được có BB đích = 0. Chỉ nomad và socket thực thi ở cả hai chain. PolyNetwork deploy được nhưng không thực thi basic block nào. Claim "đường đi cross-chain hợp lệ" hiện chưa có bằng chứng thực thi.
5. **Fixture Wormhole không deploy được trong chế độ trạng thái rỗng** (sai địa chỉ CREATE dự đoán). Fixture này có thể phụ thuộc trạng thái mainnet (nonce của deployer); cần kiểm tra lại trên fork thật.

## Hạn chế của lần chạy này

- Không có trạng thái mainnet (RPC rỗng). Kết luận (1)–(3) không phụ thuộc điều này vì nằm ở logic oracle, nhưng số BB có thể khác khi chạy fork thật.
- 20 giây × 3 seed, không phải 600 giây × 20 run.
- Output LLM là bản tháng 4 (gpt-oss-120b), không phải Gemini như paper ghi. Cần đối chiếu B7 trong todo.
- Cờ `BRIDGESENTRY_DIAG_EXEC_ONLY` là công cụ chẩn đoán, **không** phải oracle official. Nó chỉ chứng minh rằng phần thực thi hiện không đóng góp gì vào kết quả.

## Tệp

- `summary.csv`: bảng đầy đủ theo benchmark × điều kiện.
- `runs/<cond>/<bench>/seed_*.json|log`: output và log thô.
- `run_one.sh`, `aggregate.py`, `empty_rpc.py`: chạy lại toàn bộ (`xargs -P2 -L1 ./run_one.sh < jobs.txt`).
- `diag_exec_only.patch`: thay đổi 11 dòng trong `fuzz_loop.rs` để thêm cờ chẩn đoán.
- `patched/nomad/contracts/Replica.sol`: fixture Nomad đã vá (1 dòng).
