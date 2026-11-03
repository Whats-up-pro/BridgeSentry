# Phân loại 12 fixture cho đánh giá official (đề xuất, chờ xác nhận)

**Trạng thái:** đề xuất, chưa được tác giả duyệt. Các dòng ghi "CẦN XÁC NHẬN" chưa được dùng để quyết định gì.

**Nguồn gốc tài liệu:** phân loại do một phiên Claude Code cloud thực hiện ngày 03/11/2026, dựa trên post-mortem công khai và `benchmarks/<bridge>/metadata.json`. Commit gốc của phiên đó (`1610f61`) không push được vì lỗi quyền GitHub. Bản này được dựng lại từ báo cáo của phiên. Báo cáo chỉ nêu tên tổ chức phân tích (BlockSec, SlowMist, CertiK…) chứ không kèm URL, nên **cần bổ sung URL nguồn** trước khi đưa vào paper.

## Ba nhóm

- **A — lỗi logic on-chain:** được tính vào Valid Exploit Rate (VER). Phải viết official spec gồm bản lỗi và bản vá.
- **B — khoá/validator off-chain bị chiếm:** chỉ dùng để đánh giá phòng thủ chiều sâu, không tính vào VER. Harness official không cấp capability chiếm khoá.
- **C — ngoài phạm vi VER:** surrogate non-EVM, hoặc sự cố không thuộc bridge.

## Bảng phân loại

| Fixture | Nhóm | Root cause (theo báo cáo phiên cloud) | Ghi chú |
| --- | --- | --- | --- |
| nomad | A | Root `0x00` được confirm sẵn khi `initialize`. | Đã có official spec (`benchmarks/nomad/official/`). |
| qubit | A | Deposit native không kiểm `msg.value`. | Đã có official spec. Mã lỗi ở chain nguồn, nhưng metadata ghi `attack_stage: destination_chain`. Metadata còn ghi `fork.block_number` 14742532 **lớn hơn** `first_exploit_block` 14180001, tức fork sau thời điểm exploit. Chưa sửa. |
| polynetwork | A | Manager on-chain gọi được hợp đồng đích tuỳ ý (trùng selector 4 byte), nên keeper bị thay qua chính đường đi của giao thức. Không có khoá nào bị lộ (BlockSec, SlowMist, CertiK). | CẦN XÁC NHẬN quy ước nhãn stage: mã lỗi chạy ở chain thực thi thông điệp, nhưng metadata ghi `source_chain`. Còn chờ quyết định cách mô hình hoá xác minh chữ ký header của keeper. |
| socket | A | Route mới không kiểm tra calldata do người gọi truyền vào. | CẦN XÁC NHẬN: sự cố chỉ diễn ra trên một chain, không đi qua thông điệp cross-chain. Có thể không qua được cổng "đường cross-chain hợp lệ" của VER. |
| ronin | B | Khoá validator bị chiếm. | |
| harmony | B | Khoá multisig bị chiếm. | |
| multichain | B | Khoá MPC bị kiểm soát. | |
| orbit | B | Khoá multisig 7/10 bị chiếm. | Đề xuất sửa `incident_date_utc` thành 2023-12-31 (sự cố lúc khoảng 20:52 UTC ngày 31/12/2023). Metadata đang ghi 2024-01-01. Chưa sửa. |
| pgala | B | Lộ private key quản trị ProxyAdmin (theo SlowMist và đơn kiện của Gala). | CẦN XÁC NHẬN: pNetwork chưa công bố post-mortem kỹ thuật. |
| wormhole | C | Lỗi trong chương trình Solana (non-EVM). Fixture hiện là surrogate EVM. | Fixture không deploy được với RPC rỗng (`TokenBridge CREATE address mismatch`). |
| gempad | C | Token locker, không phải bridge. | CẦN XÁC NHẬN: nguồn công khai ghi lỗi reentrancy ngày 17/12/2024, lệch với ngày và root cause trong metadata. |
| fegtoken | C | DEX, không phải bridge. Lỗi là `swapToSwap` nhận `path` không được kiểm tra (15/05/2022). | CẦN XÁC NHẬN: metadata ghi 28/04/2022 và mô hình `claimMigrator`; chưa tìm thấy nguồn nào xác nhận. |

## Các mâu thuẫn trước đây và cách giải quyết

Giải quyết theo bằng chứng về root cause:

- **PolyNetwork là lỗi on-chain.** Báo cáo official ngày 03/11 xếp nó vào off-chain là sai.
- **pGALA là lỗi off-chain do lộ khoá.** Paper xếp nó là on-chain chuỗi nguồn là không có căn cứ.
- **FEGtoken là lỗi on-chain nhưng không thuộc bridge,** nên xếp nhóm C. Paper xếp nó off-chain là sai.

## Hệ quả và việc còn mở

1. Nhóm A chỉ còn nomad, qubit, polynetwork, socket, và socket còn nghi vấn. Bằng đó là quá ít để báo cáo VER. Cần bổ sung sự cố bridge on-chain trên EVM từ knowledge base 48 sự cố, có đối chiếu nguồn.
2. Chưa viết official spec cho polynetwork và socket.
3. Sửa metadata (orbit, qubit, gempad, fegtoken) cần tác giả duyệt trước. Tài liệu này không sửa metadata nào.
