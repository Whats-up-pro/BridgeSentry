# Pilot official cục bộ (2026-11-05)

Chạy bằng runner đã sửa (strict seeds + đếm `runs_failed`) để (1) hồi quy Nomad/Qubit,
(2) xác nhận runner trung thực, (3) đo nhóm fixture "dễ" dưới oracle official.

## Provenance
- Commit: `980a542` (nhánh `main`).
- rustc 1.99.1; solc 0.8.20+commit.a1b79de6; binary release sha256 `ae157dfad1bd5a90c857b6c00d1eaf830856a1839ace7a6fa84057cdc25d3b1f`.
- RPC rỗng (`scripts/official/empty_rpc.py`): **thực thi fixture cục bộ, KHÔNG phải fork mainnet**.
- 5 PRNG seed (1042–5042), 20 s/run. Môi trường: WSL Ubuntu 24.04, 16 luồng.
- Seed LLM thật chỉ có cho nomad, qubit; ronin_2024, verus dùng seed `random` (hypotheses là placeholder).

## Kết quả (`g20/summary_official.csv`)

| Fixture | Biến thể | Seed | Hợp lệ | Cảnh báo | Median TTVE (s) | runs_failed | fallback |
|---|---|---|---|---|---|---|---|
| nomad | lỗi | llm / random | 5/5 / 5/5 | 5/5 / 5/5 | 0,0115 / 0,0017 | 0 | 0 |
| nomad | vá | llm / random | 0/5 / 0/5 | 0/5 / 0/5 | > budget | 0 | 0 |
| qubit | lỗi | llm / random | 5/5 / 5/5 | 5/5 / 5/5 | 0,0046 / 0,186 | 0 | 0 |
| qubit | vá | llm / random | 0/5 / 0/5 | 0/5 / 0/5 | > budget | 0 | 0 |
| ronin_2024 | lỗi | random | 5/5 | 5/5 | 0,0011 | 0 | 0 |
| ronin_2024 | vá | random | 0/5 | 0/5 | > budget | 0 | 0 |
| verus (surrogate) | lỗi | random | 5/5 | 5/5 | 0,3843 | 0 | 0 |
| verus | vá | random | 0/5 | 0/5 | > budget | 0 | 0 |

Toàn bộ 60 run hoàn tất, **0 run lỗi, 0 fallback seed** (strict mode không âm thầm đổi sang random).
Bản lỗi: 5/5 exploit hợp lệ (qua đủ 7 cổng). Bản vá: 0 cảnh báo → đối chứng âm (hard negative) hoạt động.

## Đọc đúng
- 4 fixture này đã **bão hoà**: search ngẫu nhiên tìm ra exploit trong < 0,5 s. Không dùng để kết luận về semantic guidance.
- Verus là surrogate non-EVM (phía nguồn mô phỏng), báo **riêng**, không gộp với fixture EVM.
- Nhóm 3 fixture khó (feg_bridge_2024, crosscurve, polynetwork) **không có trong đợt này**: pilot 120 s cho nhóm khó
  bị dừng giữa chừng do máy thiếu RAM. Sẽ chạy lại trên HPC (hoặc khi đủ bộ nhớ). Smoke trước đó: 0/3 ở 120 s random.
- Chỉ là thực thi fixture cục bộ (RPC rỗng), không phải fork mainnet.
