# Mutator mở rộng: before/after trên 3 fixture khó (HPC, 2026-11-06)

So sánh cùng ngân sách, cùng điều kiện (HPC h200node02, job CPU-only mig2-35, 8 CPU),
seed `random`, 5 seed (1042–5042), **600 s/run**, RPC rỗng (fixture cục bộ, không fork mainnet).

- **before** = binary cũ (pre-mutator), sha256 `8d2c004a…`, commit `ec8f73d`. Job 10741.
- **after** = binary mutator mở rộng, sha256 `9854149f…`, commit `a90aa3d`. Job 10742.

## Bản lỗi (vulnerable): số run có exploit hợp lệ / 5

| Fixture | before | after | Median TTVE (after) |
|---|---|---|---|
| crosscurve | **0/5** | **5/5** | 0,015 s |
| feg_bridge_2024 | **0/5** | **4/5** | 156,6 s (max 226,8) |
| polynetwork | **0/5** | **1/5** | — (1 seed, ~440,7 s) |

→ Mutator mở rộng (vocab lấy từ ABI: payload ABI có cấu trúc + tên hàm) cho phép search ngẫu nhiên
dựng được exploit mà trước đó bất khả: CrossCurve giải ngay, FEG giải phần lớn, PolyNetwork chạm được 1 lần.
PolyNetwork (tấn công 2 bước, trước cutoff gpt-oss) vẫn rất khó cho random → đúng chỗ seed LLM phải chứng minh ưu thế.

## CẢNH BÁO quan trọng — bản vá chưa sạch (cần xử lý trước khi báo FPR)

Cột `runs_with_any_alert` trên **bản vá**:
- crosscurve patched: **5/5 có alert** (candidate lợi nhuận dương = 100000e18, đúng khoản thanh khoản nạp sẵn), nhưng `valid_exploits=0`.
- polynetwork patched: **5/5 có alert** (500000e18), `valid_exploits=0`.
- feg_bridge_2024 patched: 0 alert (sạch).

`valid_exploits=0` trên bản vá một phần là **do cấu trúc**: khi chạy biến thể `patched`, cổng `patched_rejected`
để `unknown` (không có "paired patched" của chính bản vá), nên không bao giờ tính là valid. Vì vậy "0 valid trên patched"
CHƯA phải bằng chứng bản vá sạch.

Tín hiệu thật là `runs_with_any_alert`: mutator mới tìm được trace rút đúng khoản thanh khoản nạp sẵn **ngay trên hợp đồng đã vá**
của CrossCurve và PolyNetwork. Nghĩa là bản vá tối giản mới chỉ chặn đúng root cause tài liệu, còn **một đường rút khác**
vẫn hở (nhiều khả năng một entrypoint release/withdraw khác cho phép chỉ định recipient tuỳ ý mà không kiểm quyền).

**Hệ quả:** trước khi báo tỷ lệ báo động giả (FPR) / đối chứng bản vá, phải **làm sạch bản vá**
(chặn mọi đường rút trái phép, không chỉ root cause tài liệu), và chứng minh giao dịch hợp lệ vẫn chạy.
FEG đã sạch; CrossCurve và PolyNetwork cần sửa fixture. Không nới mutator/oracle để che việc này.

## Đọc đúng
- VER (bản lỗi) tăng rõ rệt nhờ mutator — đây là bằng chứng cho quyết định "mở rộng mutator".
- Patched-control chưa dùng được cho CrossCurve/PolyNetwork cho tới khi fixture bản vá được làm sạch.
- Chưa có seed LLM ở đây (random). Ablation LLM+RAG / LLM-no-RAG / random (cùng mutator) là bước kế tiếp.
