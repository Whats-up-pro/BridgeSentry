# Đợt chạy official thứ 2, ngày 03/11/2026: hồi quy Nomad + Qubit

Thư mục có hậu tố `_r2` vì `experiments/official_20261103/` (đợt 1, cùng ngày) đã tồn tại. Không ghi đè đợt 1.

## Provenance

- **Commit code:** `613f64a` trên `main`. Fuzzer và fixture giống hệt `2745e02`; commit này chỉ sửa script chạy.
- **Trình biên dịch:** solc `0.8.20+commit.a1b79de6` (static linux, sha256 `0479d44f…0fda782`), `--evm-version london`.
- **Rust:** rustc 1.97.0 (2d8144b78 2026-07-07). Bản release build.
- **Seed LLM:** output gpt-oss-120b (tháng 4/2026) có sẵn trong `benchmarks/<b>/llm_outputs/`. Không gọi API LLM, không sinh lại.
- **Chế độ thực thi:** **RPC rỗng** (`empty_rpc.py`). Đây là thực thi fixture cục bộ, **không phải fork mainnet**. Block number lấy từ `metadata.json` (`fork.block_number`) và chỉ dùng làm nhãn block env.
- **Thiết lập chạy:** seed 1042, 2042, 3042, 4042, 5042. Ngân sách 20 s/run. Chạy song song 3 job trên máy 4 core.
- **Oracle:** `execution_only_asset_conservation`, đủ 7 cổng VER. Không thay đổi oracle, gate hay tolerance.

## Bước 0: kiểm tra

- `cargo test` (src/module3_fuzzing): **qua hết**, 177 + 158 passed, 0 failed (ignored: 3 + 3 + 2).
- Hồi quy khớp kỳ vọng: bản lỗi 5/5 run có exploit hợp lệ; bản vá 0/5 run có cảnh báo, cho cả hai fixture và cả hai loại seed.

## Kết quả

| Fixture | Biến thể | Seed | Run có exploit hợp lệ | Run có cảnh báo | Median TTVE | Max TTVE | Median iterations | Hành động LLM ánh xạ được |
|---|---|---|---|---|---|---|---|---|
| Nomad | lỗi | LLM | 5/5 | 5/5 | 0,0056 s | 0,0090 s | 59.163 | 15/57 |
| Nomad | lỗi | ngẫu nhiên | 5/5 | 5/5 | 0,0011 s | 0,0015 s | 55.657 | — |
| Nomad | vá | LLM | 0/5 | 0/5 | > ngân sách (censored) | — | 72.626 | 15/57 |
| Nomad | vá | ngẫu nhiên | 0/5 | 0/5 | > ngân sách (censored) | — | 63.682 | — |
| Qubit | lỗi | LLM | 5/5 | 5/5 | 0,0029 s | 0,0049 s | 19.787 | 28/65 |
| Qubit | lỗi | ngẫu nhiên | 5/5 | 5/5 | 0,0974 s | 0,2990 s | 75.491 | — |
| Qubit | vá | LLM | 0/5 | 0/5 | > ngân sách (censored) | — | 17.961 | 28/65 |
| Qubit | vá | ngẫu nhiên | 0/5 | 0/5 | > ngân sách (censored) | — | 78.801 | — |

TTVE = thời gian đến exploit hợp lệ đầu tiên. Run không trigger được tính là censored tại 20 s.

Giá trị từng seed (s):

- Nomad, LLM: 0,0070 / 0,0043 / 0,0090 / 0,0056 / 0,0025
- Nomad, ngẫu nhiên: 0,0015 / 0,0013 / 0,0008 / 0,0005 / 0,0011
- Qubit, LLM: 0,0027 / 0,0049 / 0,0022 / 0,0029 / 0,0036
- Qubit, ngẫu nhiên: 0,2990 / 0,0130 / 0,0974 / 0,0210 / 0,2567

Fixture mới: **không có**. PolyNetwork và Socket (nhóm A) chưa có official spec, nên không có số liệu ("—"). Xem `docs/official_fixture_classification.md`.

## Nhận định

1. Kết quả tái lập đợt 1 về mặt định tính. Thời gian tuyệt đối khác nhẹ do chạy song song và khác máy.
2. **Seed LLM không nhanh hơn ở Nomad**: seed ngẫu nhiên nhanh hơn khoảng 5 lần, ở mức mili giây. Ở Qubit, seed LLM nhanh hơn khoảng 30 lần theo median, nhưng cả hai loại seed đều tìm ra exploit trong dưới 0,3 s.
3. Hai fixture này **bão hoà**, nên không đủ để kết luận semantic guidance có tác dụng. Cần fixture khó hơn.
4. Tỷ lệ ánh xạ hành động LLM sang lời gọi thật vẫn thấp: 15/57 (26%) và 28/65 (43%). Nguyên nhân là output LLM được sinh cho bộ fixture cũ.

## Tệp

- `run_official.sh`: REPO lấy qua `git rev-parse`, block lấy từ metadata.
- `make_jobs.sh`, `jobs_regression.txt`, `empty_rpc.py`, `aggregate_official.py`.
- `official_runs/<b>/<variant>/<seeds>/seed_*.{json,log}`: số liệu thô.
- `summary_official.csv`: cùng cột với bản 20261103.
