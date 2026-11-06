# Hồi quy Nomad/Qubit trên HPC-UIT (2026-11-06)

Xác nhận binary musl tĩnh chạy đúng trên **compute node** HPC (Bước 1 của kế hoạch).

## Môi trường HPC
- Cụm H200, node `h200node02`, job Slurm CPU-only (KHÔNG GPU): `account=uit, partition=normal, qos=mig2-35, cpus-per-task=8, mem=8G, time=40m`. Job ID 10714.
- Binary: `bridgesentry-fuzzer` musl **tĩnh** (`statically linked`), sha256 `8d2c004ab8b6180b28050d1ab36e3fde132dd0402c2501fe3b44659ecb6dc432`, build từ commit `ec8f73d` (rustc 1.99.1, target x86_64-unknown-linux-musl).
- solc 0.8.20 static sha256 `0479d44fdf9c501c25337fdc540419f1593b884a87b47f023da4f1c700fda782`; python3 3.12.13 (`/cm/local/apps/python3/bin`).
- RPC rỗng (`empty_rpc.py`): thực thi fixture cục bộ, KHÔNG phải fork mainnet. 5 seed (1042–5042), 20 s/run. Dữ liệu ở `/datastore/dungtrt/bridgesentry`.

## Kết quả (`runs/summary_official.csv`)
| Fixture | Biến thể | Seed | Hợp lệ | Cảnh báo | Median TTVE (s) | runs_failed |
|---|---|---|---|---|---|---|
| nomad | lỗi | llm / random | 5/5 / 5/5 | 5/5 / 5/5 | 0,01 / 0,0016 | 0 |
| nomad | vá | llm / random | 0/5 / 0/5 | 0/5 / 0/5 | > budget | 0 |
| qubit | lỗi | llm / random | 5/5 / 5/5 | 5/5 / 5/5 | 0,0029 / 0,1643 | 0 |
| qubit | vá | llm / random | 0/5 / 0/5 | 0/5 / 0/5 | > budget | 0 |

40/40 run hoàn tất, **0 lỗi, 0 fallback seed**. Bản lỗi 5/5 exploit hợp lệ (đủ 7 cổng); bản vá 0 cảnh báo.
Khớp với pilot cục bộ (`official_20261105_local_pilot`) → binary HPC cho cùng kết quả.

## Kết luận Bước 1
Môi trường HPC đã nghiệm thu cho job CPU-only: binary tĩnh + solc + runner chạy đúng trên compute node,
hồi quy khớp. Chiến dịch chính có thể chạy tại đây (gom run vào ít job, qos=mig2-35 maxjobs 5).
