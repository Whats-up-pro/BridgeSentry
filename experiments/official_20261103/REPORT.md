# Oracle official (chỉ dựa trên thực thi): kết quả đầu tiên, 3/11/2026

## Đã làm

- **Module mới `official_mode.rs`**, bật bằng `BRIDGESENTRY_EVALUATION_MODE=official`. Đường official không đọc văn bản scenario làm dữ kiện oracle. LLM scenario chỉ được dùng làm **seed**: gợi ý gọi hàm nào, với tham số nào.
- **Oracle "asset conservation" dựa trên thực thi.** Một trace bị coi là vi phạm khi tập địa chỉ do kẻ tấn công kiểm soát kết thúc với số dư ròng dương ở một tài sản. Tài sản được ghép theo cặp token nguồn ↔ token đích. Số dư đọc từ log `Transfer` của các giao dịch đã commit trên cả hai chain.
- **Relay được nối vào EVM.** Event trên chain nguồn được relayer giao thật sang chain đích (faithful). Kẻ tấn công không được giả danh relayer và không được dùng chế độ tamper/replay.
- **Đủ 7 cổng VER:**
  - bytecode fixture được thực thi;
  - trạng thái thay đổi;
  - đúng capability;
  - đường gây lợi phải đi qua entrypoint release/mint của giao thức hoặc qua relay;
  - **replay** lại từ snapshot gốc ra cùng kết quả;
  - có tác động tài sản;
  - **bản vá chặn** đúng trace đó.
- **Đặc tả fixture** nằm ở `benchmarks/<bridge>/official/spec.json`:
  - lệnh deploy;
  - setup trạng thái trước sự cố (admin, nạp tiền hợp lệ của nạn nhân);
  - luật relay;
  - cặp tài sản;
  - entrypoint gốc lỗi;
  - bản lỗi và bản vá.
- **Hai fixture tham chiếu đã viết lại:**
  - **Nomad:** `initialize` với root `0x00`.
  - **Qubit:** deposit native không kiểm `msg.value`.
  - Cả hai đều có phân quyền mint, xác minh relayer và chain nguồn thật.
- **Test:** toàn bộ test Rust cũ vẫn qua (177 + 158).
- **Thay đổi oracle legacy:** chỉ đổi 1 test, test kiểm tra rằng chế độ official đang bị khóa.

## Kết quả

Thiết lập: 5 seed (1042–5042) × 20 giây cho mỗi cấu hình. Chạy fixture cục bộ với RPC rỗng, không phải fork mainnet. Output LLM dùng bản gpt-oss-120b đã commit trong repo.

| Fixture | Biến thể | Seed | Run có exploit hợp lệ | Run có cảnh báo | Median thời gian đến exploit hợp lệ | Hành động LLM ánh xạ được |
|---|---|---|---|---|---|---|
| Nomad | lỗi | LLM | 5/5 | 5/5 | 0,0089 s | 15/57 |
| Nomad | lỗi | ngẫu nhiên | 5/5 | 5/5 | 0,0013 s | — |
| Nomad | **vá** | LLM | 0/5 | **0/5** | > ngân sách | 15/57 |
| Nomad | **vá** | ngẫu nhiên | 0/5 | **0/5** | > ngân sách | — |
| Qubit | lỗi | LLM | 5/5 | 5/5 | **0,0040 s** | 28/65 |
| Qubit | lỗi | ngẫu nhiên | 5/5 | 5/5 | 0,0997 s | — |
| Qubit | **vá** | LLM | 0/5 | **0/5** | > ngân sách | 28/65 |
| Qubit | **vá** | ngẫu nhiên | 0/5 | **0/5** | > ngân sách | — |

Mỗi run thử khoảng 16.000–55.000 trace. Không có cảnh báo nào trên bản vá, tức FPR trên hard negative là 0/20 run.

## Đọc kết quả cho trung thực

1. **Oracle mới phân biệt được bản lỗi và bản vá.** Oracle cũ không làm được: Nomad đã vá vẫn trigger 18/18 invariant.
2. **Seed từ LLM chỉ giúp ở Qubit** (median nhanh hơn khoảng 25 lần). **Ở Nomad thì không**, seed ngẫu nhiên còn nhanh hơn. Lý do là hai fixture này nhỏ (4–5 hợp đồng, vài hàm), fuzzer ngẫu nhiên cũng chạm tới lỗi trong vài mili giây. Muốn chứng minh semantic guidance có tác dụng thì cần fixture khó hơn: chuỗi nhiều bước, nhiều hàm gây nhiễu, điều kiện tham số hẹp. Nếu không, benchmark lại bão hoà, đúng như reviewer đã chỉ ra.
3. **Tỷ lệ ánh xạ hành động LLM sang lời gọi thật còn thấp** (26–43%). Bản thân con số này là một kết quả cho RQ1 (semantic fidelity). Lưu ý: output LLM được sinh cho bộ fixture cũ, nên tên hợp đồng/hàm không khớp hoàn toàn với fixture official.
4. **Lỗi off-chain** (Ronin, Harmony, Multichain, Orbit, PolyNetwork, pGALA) đòi hỏi capability chiếm khoá. Harness official không cấp capability này, nên các case đó phải báo riêng là "phòng thủ chiều sâu", không tính vào VER.

## Trạng thái todo.txt sau bước này

| Mục | Trạng thái |
|---|---|
| A2 patched control | **Đã có cơ chế + kết quả cho 2/12 fixture.** Còn: Socket, GemPad, FEGtoken, Wormhole, (PolyNetwork, pGALA nếu mô hình hoá được phần on-chain) |
| A3 benign/hard negative | Hard negative = bản vá: FPR 0/20 run trên 2 fixture. Còn: bridge lành tính độc lập |
| A7 phân phối thời gian | Đã có median/max, run không trigger tính là censored. Cần nhiều seed hơn (20) và vẽ survival curve |
| A1 BridgeFuzz | Chưa. Cần kiểm tra artifact công khai |
| A4 holdout, A5 parser-only, A8 token/latency | Chưa. Cần sinh lại output Module 1–2 bằng LLM (cần key API hoặc GPU HPC). Nên sinh lại **đúng cho fixture official** để tên khớp |
| A6 reorg | Chưa |
| A9 inter-rater | Với oracle mới thì cảnh báo đã được dedupe theo root cause. Cần quyết định lại có còn cần không |
| B1 | Output ATG/hypotheses đúng là do Module 1–2 sinh ra (bản commit trong repo, gpt-oss-120b, tháng 4/2026), nhưng oracle legacy **không dùng kết quả thực thi**. Paper phải nói rõ điều này |
| B2 | Distance của authorization/uniqueness trong `checker.rs` là heuristic của oracle legacy: margin locked−minted (+5/+10), hằng số 50 hoặc 25. Không nên đưa vào paper; thay bằng mô tả oracle official |
| B3 | Code legacy: trọng số seed khởi tạo bằng `confidence` của scenario, sau mỗi lần chạy nhân với (1 + 0,5·R). Seed mới có trọng số R. Tức **không phải** "reward của lần chạy gần nhất" như paper đang viết |
| B4 | `run_full_sweep_real.sh`: mặc định RUNS=20, seed = r·1000+42. Khớp với "20 seed/fixture" |
| B5 | Cần bạn xác nhận số core được cấp |
| B6 | `benchmarks/orbit/metadata.json` ghi `incident_date_utc: 2024-01-01`, tên file KB là `orbit_20240101`. Nếu sự cố thực tế là 31/12/2023 UTC thì phải sửa metadata cho thống nhất với paper |
| B7 | **Mâu thuẫn:** output LLM trong repo là gpt-oss-120b (NVIDIA API), còn paper ghi Gemini/GPT-4o. Cần chọn một model, sinh lại và ghi provenance |
| B8 | Kết quả official ghi số PC duy nhất của fixture (Nomad 4.520, Qubit 2.438). Số basic block của oracle legacy không còn ý nghĩa |

## Tệp

- `official_oracle_2026-11-03.patch`: toàn bộ thay đổi so với commit `db20af7`. Áp bằng `git apply`.
- `summary_official.csv`, `official_runs/`: số liệu thô.
- Chạy lại: `BRIDGESENTRY_EVALUATION_MODE=official BRIDGESENTRY_OFFICIAL_VARIANT=vulnerable|patched BRIDGESENTRY_OFFICIAL_SEEDS=llm|random`, với `solc` 0.8.20 trong PATH và `--source-rpc/--dest-rpc` trỏ tới RPC (mainnet fork hoặc `empty_rpc.py`).
