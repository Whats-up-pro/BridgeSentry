# Kế hoạch hợp nhất: hoàn thiện thực nghiệm và kết quả định lượng cho paper BridgeSentry

**Phiên bản:** 05/11/2026. Đây là kế hoạch thực thi **duy nhất**. Nó gộp hai bản:
- bản kế hoạch chi tiết "Hoàn thiện thực nghiệm và kết quả định lượng cho paper" do một phiên khác soạn, dựa trên commit `25b4fa7`;
- 8 điều chỉnh Đ1–Đ8 đã được người dùng duyệt (`PLAN_dieu_chinh_truoc_trien_khai_2026-11-04.md`).

Kế hoạch tổng quát trước đó (`PLAN_thuc_nghiem_A_2026-11-04.md`) chỉ để tham khảo bối cảnh. Khi có mâu thuẫn, làm theo file này.

Lưu ý: bản chi tiết gốc được người dùng dán thành hai đoạn, có một khoảng hở nhỏ ở cuối Bước 6 (sau câu "khoảng 99 giờ CPU tìm kiếm"). Nội dung trong khoảng hở được thay bằng Đ2 và Đ6.

---

## 1. Mục tiêu, điểm bắt đầu, lựa chọn đã chốt

**Mục tiêu:** hoàn thành các mục trong `todo.txt` (A1–A9, B1–B8, C1–C6) bằng: cấu hình tái lập được, dữ liệu có đối chứng, bảng/hình định lượng, và nội dung paper khớp với bằng chứng.

**Trạng thái repo `Whats-up-pro/BridgeSentry`, `main` = `25b4fa7`:**

| Hạng mục | Trạng thái |
|---|---|
| Nomad, Qubit | Hai đợt kết quả official: bản lỗi 5/5 exploit hợp lệ, bản vá 0/5 cảnh báo |
| 5 fixture mới (feg_bridge_2024, crosscurve, ronin_2024, polynetwork, verus) | Có bản lỗi, bản vá, test xác định; còn phải rà nguồn và kiểm chứng |
| Smoke 04/11, seed ngẫu nhiên | Ronin-2024 (median 0,0006 s) và Verus (0,36 s) tìm ra exploit; FEG, CrossCurve, PolyNetwork 0/3 ở cả 20 s và 120 s; mọi bản vá 0 cảnh báo |
| Binary Linux tĩnh (musl) | Có hướng dẫn build và hồi quy (`experiments/official_20261104_musl_regression/`); chưa thử trên compute node HPC |
| Kiểm toán KB (`docs/kb_audit.md`) | Bản nháp 48 dòng; nguồn chủ yếu mới kiểm qua tóm tắt tìm kiếm, chưa đủ để khoá dữ liệu |
| Holdout, sinh lại seed, thống kê | Chưa làm |

**Đã chốt:**
- Model chính: gpt-oss-120b qua NVIDIA API. Thêm một model OpenAI làm đối chứng; tên đề xuất `gpt-6.1-sol`, phải kiểm tra quyền truy cập trước khi khoá cấu hình. Báo cáo tách theo model, không gộp backend.
- Trần chi phí API cho cả chiến dịch: **25 USD**, đã tính cả pilot, retry và mọi lời gọi tính phí.
- Build trên Linux/cloud. Fuzzing chạy bằng CPU qua Slurm trên HPC, theo `Huong_dan_HPC_dungtrt.pdf`: không tính toán trên login node, dữ liệu để ở `/datastore/dungtrt`, mỗi job ≤ 3 ngày, ≤ 3 job song song, ≤ 50 job chờ. Thầy đã cho phép job chỉ dùng CPU.
- **Không chạy job GPU nào khi chưa báo người dùng và được đồng ý.** Kế hoạch này không cần GPU.
- Mọi chiến dịch mới dùng oracle official (`BRIDGESENTRY_EVALUATION_MODE=official`) và runner `scripts/official/`. Các thư mục `experiments/official_*` đã có là hồ sơ đóng băng, không sửa.
- Làm trực tiếp trên `main`: `git pull --rebase` trước khi push, không force-push.
- Không bịa số. Chưa có artifact thì ghi "—" kèm lý do. Kết quả LLM không vượt random vẫn là kết quả hợp lệ, phải báo cáo đầy đủ.

---

## 2. Các bước và điều kiện nghiệm thu

### Bước 0 — Đồng bộ trạng thái, khoá quy trình chạy
1. Đồng bộ `main`; ghi commit hiện tại và kiểm tra thay đổi chưa commit.
2. Lập bảng theo dõi A1–A9, B1–B8, C1–C6. Mỗi mục ghi: trạng thái, bằng chứng, việc còn thiếu, điều kiện hoàn thành.
3. Đối chiếu hồ sơ ngày 03–04/11 với mã nguồn; tách rõ test xác định, smoke và thực nghiệm chính.
4. Ghi các quy tắc cố định: định nghĩa exploit hợp lệ, đơn vị thống kê, nguồn dữ liệu, ngân sách, cách xử lý lỗi.

**Đạt khi:** mọi mục có trạng thái cụ thể; không dựa vào thông tin local cũ để quyết định làm lại việc đã có trên repo.

### Bước 1 — Xác nhận môi trường HPC
1. Kiểm tra binary tĩnh; nếu không lấy được đúng artifact thì build lại bằng toolchain có ghi nhận.
2. Ghi SHA-256 của binary, phiên bản Rust và solc, và các dependency đã khoá.
3. Dùng `sinfo` / `scontrol show partition` (chỉ đọc) để xác định partition nhận job CPU. Chạy một job thử: 2 CPU, 4 GB RAM, tối đa 1 giờ, không xin GPU.
4. Chép binary, solc và mã nguồn đúng commit lên `/datastore/dungtrt` bằng `scp`. Mọi tính toán chỉ chạy trên compute node.
5. Hồi quy Nomad/Qubit bằng chính binary đó trên HPC: hai loại seed, bản lỗi/bản vá, 5 seed, 20 s.
6. Kiểm tra log, mã thoát, CPU/RAM thực tế, thời gian setup.

**Đạt khi:** mọi run hoàn tất; bản lỗi tái hiện được exploit, bản vá không cảnh báo; không test nào bị bỏ qua vì thiếu công cụ.

Nếu Slurm từ chối job CPU: ghi nguyên nhân, báo người dùng, **không tự chuyển sang job GPU**.

### Bước 2 — Độ trung thực của bảy fixture và khả năng biểu diễn exploit
Thứ tự: Nomad/Qubit (làm chuẩn) → FEG → CrossCurve → Ronin-2024 → PolyNetwork → Verus.

Với từng fixture:
1. Đọc toàn văn post-mortem hoặc nguồn kỹ thuật gốc. Đối chiếu hàm lỗi, điều kiện khai thác, chuỗi giao dịch, cách sửa.
2. Tách rõ bản vá thật của dự án với bản sửa dựng cho mô hình tối giản.
3. Kiểm tra quyền của attacker, admin, relayer/notary và dữ liệu nguồn. Attacker không được có quyền vượt mô hình đe doạ.
4. Test xác định: chuỗi tấn công đã biết có lợi nhuận trên bản lỗi; cùng trace đó không có lợi nhuận trên bản vá.
5. Kiểm tra giao dịch hợp lệ vẫn thành công trên bản vá, để bản vá không "chặn tất cả".
6. **(Đ1) Khả năng biểu diễn:** viết chuỗi tấn công dưới dạng chuỗi hành động mà fuzzer tạo ra được (`Seq` trong `official_mode.rs`), chỉ dùng thao tác mà mutator/seed sinh được. Cho chuỗi này qua pipeline xác nhận đầy đủ: phải ra exploit hợp lệ trên bản lỗi và không có lợi nhuận trên bản vá. Nếu exploit cần thao tác ngoài không gian hành động (ví dụ deploy hợp đồng của kẻ tấn công rồi gửi thông điệp từ hợp đồng đó), **dừng lại và báo người dùng** chọn một trong hai:
   - mở rộng không gian hành động (có test, mô tả trong paper);
   - ghi fixture là "không biểu diễn được trong harness hiện tại".
7. Chỉ sửa fixture khi có sai lệch đã được chứng minh. Sửa xong thì chạy lại test và smoke vào thư mục mới.

**Đạt khi:** mỗi fixture có nguồn kiểm chứng, có test thực thi trên cả hai phiên bản, và **đã qua Đ1**. Fixture chưa qua Đ1 thì không vào ma trận chính. Fuzzer không tìm ra exploit vẫn là một kết quả, không phải lý do để làm lỗi dễ hơn.

Verus được báo riêng vì phía nguồn là surrogate của chain non-EVM. Mọi kết quả tổng hợp phải tách 6 fixture EVM khỏi Verus.

### Bước 3 — Hoàn thiện KB và đối chứng âm
**KB:**
1. Hoàn thiện `docs/kb_audit.md` bằng nguồn đã thực sự đọc được; sửa các lỗi đếm trùng và tổng hợp trong bản nháp.
2. Gán ID sự cố chuẩn, bảng alias và nhóm lỗ hổng nhất quán.
3. Record chưa xác minh hoặc ngoài phạm vi thì đưa ra khỏi snapshot thực nghiệm, nhưng giữ dữ liệu gốc để truy vết.
4. Tạo snapshot chuẩn hoá từ danh sách sửa/loại, mỗi mục có lý do và nguồn. Thêm record đã xác minh cho các sự cố mới.
5. Tính hash nội dung snapshot; công bố số record và số sự cố thực tế sau chuẩn hoá.

**Đối chứng âm:**
- Bảy bản vá đóng vai hard negative.
- Thêm hai bridge lành tính độc lập: một lock/mint và một messaging.
- Có test cho thấy luồng hợp lệ chạy được, và các trường hợp sai quyền, sai nguồn thông điệp, dùng lại nonce đều bị từ chối.

**Đạt khi:** mọi record được dùng đều có nguồn và danh tính sự cố rõ; bộ đối chứng âm hoạt động đúng về chức năng.

### Bước 4 — Holdout và runner
Năm chế độ retrieval:

| Chế độ | Quy tắc |
|---|---|
| known | Được truy xuất sự cố đích trong KB đã chuẩn hoá |
| **no_rag (Đ3)** | Không truy xuất; LLM sinh seed chỉ từ hợp đồng/ABI |
| exact | Loại sự cố đích cùng mọi alias/bản trùng |
| temporal | Áp dụng exact; chỉ giữ sự cố trước ngày của sự cố đích; loại record thiếu ngày hoặc ngày không hợp lệ |
| family | Áp dụng exact và loại cùng nhóm lỗ hổng. **Chỉ chạy nếu còn ngân sách, và chỉ trên 3 fixture khó (Đ3)** |

Bộ lọc chạy trước khi xây index/truy xuất. Ghi lại: ID được phép, ID bị loại kèm lý do, ID thực sự được truy xuất.

**Runner:**
- Nhận thư mục seed và mã cấu hình; xác định fixture độc lập với vị trí file seed/ATG. Giữ cách gọi cũ để tái lập hồ sơ trước.
- Thiếu seed, thiếu model hoặc lỗi API đều phải được ghi rõ; không âm thầm thay backend hay thay bằng seed ngẫu nhiên.
- Truyền đúng mã lỗi của fuzzer. Run thiếu JSON, crash hoặc cấu hình sai bị đánh dấu là lỗi thực thi.
- Mỗi job dùng cổng RPC riêng, có kiểm tra sẵn sàng và dọn tiến trình khi kết thúc.
- Cho phép chạy tiếp các run còn thiếu khi cấu hình khớp; giữ lịch sử các lần chạy lỗi.
- Manifest sinh dữ liệu lưu: model, tham số, hash nguồn/corpus/prompt, ID retrieval.
- Manifest chạy lưu: fixture, variant, cấu hình seed, PRNG seed, budget, phần cứng, checksum binary.
- Kết quả phân biệt bốn loại: lỗi hạ tầng, lỗi sinh dữ liệu, run hoàn tất không tìm thấy, exploit hợp lệ. Vẫn đọc được dữ liệu cũ; muốn đổi nghĩa trường cũ thì phải ghi phiên bản.

**Đạt khi:** test bao phủ alias, mốc thời gian, corpus rỗng, seed thiếu, crash, chạy song song, chạy tiếp chiến dịch; không có kết quả nào bị ghi đè giữa các cấu hình.

### Bước 5 — Sinh lại dữ liệu Module 1–2, chi phí, parser-only
1. Đầu vào pipeline chỉ gồm mã hợp đồng/ABI cần thiết. Loại README, patch, test khai thác và mọi chú thích tiết lộ đáp án.
2. Sinh trên đúng fixture official; lưu hash nguồn, prompt, KB, cấu hình và kết quả thô.
3. Khoá provider/model; trong một model, giữ cùng prompt và cấu hình cho mọi regime.
4. Parser-only: tắt LLM ở Module 1 bằng cấu hình riêng; Module 2 vẫn dùng gpt-oss. Kiểm tra số lời gọi LLM của Module 1 bằng 0.
5. Probe ghi nhớ: chạy trong phiên độc lập, không đưa câu trả lời của probe vào quá trình sinh seed. Probe chỉ là tín hiệu tham khảo; kết quả âm không chứng minh model chưa từng thấy sự cố.
6. Ghi: token, chi phí, latency, retry, lỗi JSON, fallback, tỷ lệ ánh xạ hành động.
7. **(Đ4) Phương sai của LLM:** với 3 fixture khó (FEG, CrossCurve, PolyNetwork), mỗi cấu hình gpt-oss sinh **3 bộ output độc lập** (temperature > 0, ghi tham số). Nhóm dễ và model OpenAI: 1 bộ, ghi rõ giới hạn.

**Ngân sách 25 USD:** pilot tối đa 3 USD, sinh chính 19 USD, dự phòng 3 USD. Kiểm tra chi phí tối đa dự kiến trước mỗi lời gọi; retry cũng tính vào trần.

**Đạt khi:** mọi đầu ra dùng được, hoặc thất bại có ghi rõ; không có seed giả; không chọn lại đầu ra dựa trên kết quả fuzzing; không vượt trần chi phí.

### Bước 6 — Pilot, khoá ma trận, chạy thực nghiệm chính
**(Đ2) Pilot ngân sách** trước khi khoá:
- Chạy bản lỗi của FEG, CrossCurve, PolyNetwork với seed `random` và `gpt-oss/known`, **600 s × 5 seed**. Ghi vào thư mục `experiments/` riêng.
- Quy tắc ngân sách, áp dụng chung cho mọi cấu hình của cùng một fixture:
  - nhóm dễ (Nomad, Qubit, Ronin-2024, Verus): 120 s;
  - nhóm khó: 600 s nếu pilot có cấu hình tìm ra exploit sau mốc 120 s, ngược lại 120 s.
- Không dùng pilot để chọn lại output LLM.

**Khoá:**
- PRNG seed: 1000 × r + 42, với r = 1…20.
- Cùng phần cứng, oracle, giới hạn corpus và độ dài trace; ghi số seed thực tế.
- Mỗi run một worker; số worker không vượt số CPU Slurm cấp. Gom nhiều run vào ít job (`xargs -P` trong job).

**Ma trận chính (Đ3):**

| Nhóm seed | Cấu hình |
|---|---|
| Random | 1 |
| gpt-oss-120b | known, no_rag, exact, temporal |
| OpenAI đối chứng | known, exact, temporal |
| Parser-only + gpt-oss ở Module 2 | known, exact |

- 7 fixture × 2 biến thể × 10 cấu hình × 20 seed = 2.800 run. Với 3 fixture khó, mỗi cấu hình gpt-oss có 3 bộ output (Đ4); có thể dùng 10 seed cho mỗi bộ để giữ tổng số run.
- 2 bridge lành tính: random, gpt-oss/known, OpenAI/known, parser-only/known × 20 seed = 160 run. Không gán ngày sự cố giả để tạo temporal holdout.

**(Đ6) Khối lượng CPU:** khoảng 99 giờ nếu mọi fixture dùng 120 s; khoảng 250–300 giờ nếu nhóm khó cần 600 s. Con số chưa gồm thời gian xác nhận, baseline và reorg. Đổi ra thời gian thực sau khi biết số CPU Slurm cấp.

**Thứ tự cắt khi trễ hoặc thiếu CPU:**
1. A6 rollback/reorg (snapshot đồng bộ trình bày là lựa chọn thiết kế, theo Option A);
2. nhóm dễ giảm còn 10 seed, bỏ cấu hình OpenAI/exact;
3. A1 rút gọn, chỉ giữ ItyFuzz đơn chain trên tập tương thích.

Không cắt: 3 fixture khó, bản vá, benign, các cấu hình random / gpt-oss known / no_rag / temporal.

**Đạt khi:** đủ số run của các cấu hình đã khoá; lỗi hạ tầng được xử lý hoặc ghi rõ trạng thái chưa hoàn tất. Không loại fixture khó vì kết quả thấp.

### Bước 7 — Thống kê và trả lời câu hỏi nghiên cứu
- Tỷ lệ run có exploit hợp lệ theo fixture/cấu hình, kèm CI 95%.
- Tỷ lệ run có cảnh báo trên bản vá và trên benign, báo riêng từng nhóm.
- Kaplan–Meier cho thời gian tới ứng viên được xác nhận; run không tìm ra thì censored tại mốc ngân sách.
- Median/IQR chỉ báo khi ước lượng được; không tính chỉ trên các run thành công.
- **(Đ5) So sánh không ghép cặp, trong từng fixture:** log-rank cho survival, Fisher exact cho tỷ lệ; độ lớn hiệu ứng (hiệu tỷ lệ, tỷ số median TTVE) có CI 95% bootstrap; hiệu chỉnh Holm trên họ so sánh khai báo trước:
  - random vs gpt-oss/known;
  - known vs no_rag;
  - known vs exact;
  - known vs temporal;
  - gpt-oss vs OpenAI;
  - LLM-Module1 vs parser-only.
- Không gộp run của nhiều fixture thành một tỷ lệ. VER tính ở đơn vị sự cố (6 EVM + 1 surrogate, báo riêng).
- Kết luận về semantic guidance chỉ dựa trên 3 fixture khó. PolyNetwork (2021) xảy ra trước cutoff của gpt-oss nên có thể bị nhiễm; FEG (12/2024) và CrossCurve (01/2026) là phép thử sạch.
- Tách thời gian: sinh dữ liệu, setup, tìm kiếm, xác nhận, tổng.
- Báo cáo tỷ lệ lỗi sinh, tỷ lệ ánh xạ hành động, số PC thực thi, mỗi chỉ số có định nghĩa rõ.
- Chạy lại script thống kê trên dữ liệu cũ đã biết số để kiểm tra.

**Đầu ra:** CSV cuối, bảng LaTeX, hình survival, phần giải thích từng kết quả.

**Đạt khi:** chạy lại từ dữ liệu thô tái tạo được bảng/hình; kết luận tách được hiệu quả tìm kiếm, hiệu quả toàn pipeline và giới hạn của bằng chứng.

### Bước 8 — So sánh BridgeFuzz và ItyFuzz (A1)
- Kiểm tra artifact và hướng dẫn chính thức ngay từ đầu; chuẩn bị thư xin artifact nếu cần.
- So sánh sau khi pipeline chính đã ổn định, trên cùng fixture tương thích, phần cứng, ngân sách, quy tắc xác nhận.
- ItyFuzz báo rõ là phạm vi đơn chain; kiểm tra có chuyển trace về oracle chung được không.
- Không dùng bản tái hiện nội bộ như thể đó là công cụ gốc.

**Đạt khi:** có kết quả so sánh tái lập được trên tập tương thích, hoặc có hồ sơ chỉ rõ phần không làm được vì thiếu artifact/không tương thích. Các trường hợp đó **không được ghi thành 0%**.

### Bước 9 — Rollback/reorg (A6), cắt đầu tiên nếu trễ
- Hai kịch bản có kiểm soát: rollback chain nguồn sau khi thông điệp đã được giao; rollback chain đích trước khi thông điệp được thực thi lại.
- Reorg là điều kiện môi trường, không cấp thêm quyền cho kẻ tấn công. Báo cáo tách khỏi VER.
- So sánh khôi phục đồng bộ với biến thể không đồng bộ, cùng trace, seed, ngân sách.
- Kiểm tra tính nhất quán của hai EVM, hàng đợi relay và trạng thái theo dõi tài sản của oracle.
- Báo tỷ lệ replay đúng, cảnh báo sai, exploit hợp lệ.

**Đạt khi:** có kết quả thực nghiệm cho A6, kể cả khi hai cấu hình không khác nhau. Chỉ gọi snapshot đồng bộ là đóng góp khi số liệu ủng hộ.

### Bước 10 — Hoàn thiện paper, đóng từng mục TODO
**(Đ7) Viết song song, không dồn vào tuần cuối:**
- sau Bước 2: đoạn mô tả fixture, kèm giới hạn mô hình hoá;
- sau Bước 3: Table 2 theo phân loại mới, và số record KB sau chuẩn hoá (thay "48 incidents" ở mọi chỗ);
- sau pilot: đoạn Setup (ngân sách, phần cứng, commit).

Nội dung sửa ở **cả** `main.tex` và `main_bcra.tex`. Định dạng riêng của BCRA chỉ sửa ở `main_bcra.tex`. Giữ nguyên `\documentclass[a4paper]{cas-sc}`.

**Phần B:**
- Đối chiếu đường đi thật của output Module 1–2 vào fuzzer.
- Mô tả đúng checker, trọng số/reward và những thành phần thực sự được đánh giá.
- Ghi seed, số CPU được cấp, model/version và ngày truy cập, lấy từ manifest.
- Thống nhất ngày sự cố và vị trí lỗi theo nguồn đã xác minh.
- Phân biệt PC với basic block; dữ liệu legacy chỉ dùng trong phạm vi chẩn đoán oracle.

**Phần C:**
- Cập nhật Abstract, bảng benchmark, Evaluation, Discussion, Limitations, Conclusion theo số liệu cuối.
- Kiểm tra acknowledgement/funding, ORCID, các mục khai báo.
- Rà tài liệu tham khảo; thay preprint bằng bản đã công bố khi đã xác minh.
- Xuất hình vector từ nguồn draw.io có sẵn. **(Đ8)** `img/` chỉ có nguồn cho kiến trúc, Module 2, Module 3; Module 1 không có nguồn, nên giữ PNG hoặc vẽ lại, ghi rõ lựa chọn. Hình kết quả mới chỉ dùng dữ liệu hợp lệ.
- Đóng gói code, cấu hình, prompt, snapshot KB, dữ liệu thô, lệnh tái tạo; chuẩn bị metadata lưu trữ/DOI; ghi đúng trạng thái công bố thực tế.
- Compile và kiểm tra PDF: bảng tràn, hình, citation, cross-reference.

**A9:** ghi rõ không còn áp dụng cho con số legacy đã rút. Không gọi khoá khử trùng ứng viên hiện tại là "root cause đã được xác nhận" khi chưa có đối chiếu tương ứng.

**Đạt khi:** mọi mục TODO có kết quả, bằng chứng đã xác minh, lý do không áp dụng, hoặc hạn chế được trình bày rõ. Không đánh dấu xong chỉ vì đã viết mã.

---

## 3. Lịch dự kiến

| Thời gian | Mốc |
|---|---|
| 05–07/11 | Bước 0–1; Bước 2 kèm Đ1 cho 3 fixture khó trước tiên |
| 08–12/11 | Nghiệm thu KB/fixture, đối chứng âm, holdout, sinh dữ liệu |
| 13–17/11 | Pilot 600 s, khoá ma trận, chiến dịch chính, thống kê |
| 18–23/11 | Baseline (A1), rollback/reorg (A6) nếu còn thời gian |
| 24–30/11 | Chạy bù, hoàn thiện paper, artifact, kiểm tra cuối |

Chỉ chuyển mốc khi đạt điều kiện nghiệm thu. Phần nào phụ thuộc bên ngoài mà chưa có thì làm tiếp các phần độc lập và ghi rõ trạng thái.

**Kết thúc khi:**
- có kết quả định lượng cuối, truy được đến dữ liệu thô;
- có phân tích đối chứng và giới hạn rõ;
- paper, bảng, hình, artifact thống nhất với nhau;
- mọi mục TODO được đóng bằng bằng chứng.
