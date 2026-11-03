# Phân loại 12 fixture cho đánh giá official (đề xuất, chờ xác nhận)

**Trạng thái:** đề xuất, chưa được tác giả duyệt. Các dòng ghi "CẦN NGƯỜI DÙNG XÁC NHẬN" chưa được dùng để quyết định gì. Tài liệu này không sửa metadata nào.

**Nguồn gốc:** phiên Claude Code cloud ngày 03/11/2026 (commit gốc `1610f61`, kèm URL nguồn). Bản này gộp thêm các phát hiện của bản dựng lại `ed24e28`: fork block của Qubit và lỗi deploy của Wormhole.

Nhóm: **(A)** lỗi logic on-chain của bridge, tính vào VER; **(B)** khoá/validator off-chain bị chiếm, chỉ dùng cho đánh giá phòng thủ chiều sâu, không tính VER; **(C)** báo riêng: surrogate non-EVM, hoặc sự cố không thực sự thuộc bridge.

"Stage" ghi vị trí của mã/khoá có lỗi: on-chain chain nguồn, on-chain chain đích (chain thực thi thông điệp đến), off-chain, hoặc non-EVM.

| Fixture | Root cause (tóm tắt) | Stage | Nhóm | Nguồn | Mức chắc chắn | Ghi chú |
|---|---|---|---|---|---|---|
| polynetwork | `EthCrossChainManager.verifyHeaderAndExecuteTx` gọi hợp đồng đích tuỳ ý do thông điệp chỉ định. Một thông điệp được dựng sao cho selector trùng `EthCrossChainData.putCurEpochConPubKeyBytes`; vì Manager là owner của Data nên keeper bị thay. Sau đó kẻ tấn công ký rút tiền bằng keeper mới. **Không có private key nào bị lộ.** | On-chain, phía chain thực thi thông điệp (chain đích của thông điệp) | **A** | BlockSec: https://blocksec.com/blog/the-further-analysis-of-the-poly-network-attack ; SlowMist: https://slowmist.medium.com/the-root-cause-of-poly-network-being-hacked-ec2ee1b0c68f ; CertiK: https://certik.medium.com/polynetwork-hack-analysis-a86513f2a730 ; Rekt: https://rekt.news/polynetwork-rekt/ | Cao (on-chain); trung bình (nhãn nguồn/đích) | Giải mâu thuẫn: báo cáo official xếp off-chain là **sai**, vì keeper bị thay bằng đường on-chain của chính giao thức. Paper ghi "on-chain chain nguồn"; metadata ghi `attack_stage: source_chain`, `attack_type: key_compromise`. Hợp đồng lỗi chạy ở chain nhận và thực thi thông điệp. Trong benchmark, chain đó (Ethereum) được gán nhãn "source". **CẦN NGƯỜI DÙNG XÁC NHẬN** quy ước nhãn stage. Fixture official chưa viết, xem mục cuối. |
| wormhole | Chương trình Solana `verify_signatures` không kiểm tra account sysvar instructions là account chuẩn, nên VAA giả được chấp nhận và whETH được mint. | Non-EVM (Solana) | **C** | Rekt: https://rekt.news/wormhole-rekt/ ; Extropy (metadata) | Cao | Fixture EVM chỉ là surrogate, báo riêng. Fixture không deploy được với RPC rỗng (`TokenBridge CREATE address mismatch`). |
| ronin | 5/9 khoá validator bị chiếm (4 của Sky Mavis + 1 của Axie DAO qua allowlist gas-free cũ). | Off-chain | **B** | KB nội bộ (`benchmarks/ronin/metadata.json`); Rekt: https://rekt.news/ronin-rekt/ | Cao | |
| nomad | `Replica.initialize` với `_committedRoot = 0x00` đặt `confirmAt[0x00]=1`, nên thông điệp chưa được chứng minh vẫn qua `acceptableRoot`. | On-chain, chain đích (Replica) | **A** | KB nội bộ; tham chiếu trong metadata | Cao | Đã có fixture official. |
| harmony | 2/5 khoá multisig của Horizon bridge bị chiếm. | Off-chain | **B** | KB nội bộ; Rekt: https://rekt.news/harmony-rekt/ | Cao | |
| multichain | Khoá MPC bị kiểm soát/chiếm (sau khi CEO bị bắt); rút tiền bằng chữ ký hợp lệ. | Off-chain | **B** | KB nội bộ | Cao | |
| socket | Route mới thêm vào SocketGateway (`performAction`) không kiểm tra `swapExtraData` trước khi dùng nó trong lời gọi, nên lời gọi `transferFrom` trên approval của người dùng bị chèn vào. | On-chain, chain nguồn (gateway giữ approval) | **A** | Halborn: https://www.halborn.com/blog/post/explained-the-socket-protocol-hack-january-2024 ; CertiK: https://www.certik.com/zh-CN/blog/socket-tech-incident-analysis ; CoinDesk: https://www.coindesk.com/tech/2024/01/17/socket-bungee-restart-operations-after-apparent-33m-exploit | Cao (root cause); trung bình (nhóm) | Sự cố đơn chain: không đi qua thông điệp cross-chain nào, dù Socket là hạ tầng bridge-aggregator. **CẦN NGƯỜI DÙNG XÁC NHẬN** việc tính vào VER; có thể không qua cổng "đường cross-chain hợp lệ" nếu spec đặt `cross_chain: true`. Fixture official chưa viết. |
| orbit | 7/10 khoá multisig (farmer) bị chiếm; chi tiết vận hành chưa công bố đầy đủ. | Off-chain | **B** | Rekt: https://www.rekt.news/orbit-bridge-rekt ; The Block: https://theblock.co/post/269809/orbit-chains-bridge-reportedly-hacked-for-81-5-million ; Halborn: https://halborn.com/blog/post/explained-the-orbit-bridge-hack-december-2023 | Cao (off-chain); trung bình (cơ chế chính xác) | **Ngày:** thông báo của Orbit ghi 31/12/2023, 20:52:47 UTC. **Đề xuất** sửa `incident_date_utc` thành `2023-12-31` (paper đã ghi 2023). Metadata **chưa được sửa** theo yêu cầu. |
| gempad | Theo nguồn công khai: sự cố ngày 17/12/2024, reentrancy trong hợp đồng lock của GemPad (`collectFees`/withdraw) trên BSC/ETH/Base/Polygon, khoảng 1,9 triệu USD. | On-chain, nhưng **không phải bridge** (token locker) | **C** | GemPad: https://medium.com/@thegempad/gempad-lockv2-exploit-20eb75930eb8 ; Halborn: https://www.halborn.com/blog/post/explained-the-gempad-hack-december-2024 ; Rekt: https://rekt.news/gempad-rekt | Cao (không phải bridge) | **Mâu thuẫn với metadata:** metadata ghi `2024-04-13` và root cause `transferLockOwnership` thiếu kiểm quyền; không tìm thấy nguồn nào xác nhận hai thông tin này. **CẦN NGƯỜI DÙNG XÁC NHẬN** nguồn gốc của mô hình trong repo. |
| fegtoken | Theo nguồn công khai: ngày 15–16/05/2022, `FEGexPRO.swapToSwap` nhận tham số `path` không được kiểm tra, dẫn đến approve tuỳ ý; kết hợp lệch số dư nội bộ và flash loan. | On-chain, nhưng **không phải bridge** (DEX FEGexPRO, hai sự cố độc lập trên BSC và ETH) | **C** | BlockSec: https://blocksec.com/blog/the-analysis-of-fegtoken-security-incident-devils-in-the-details ; CertiK: https://www.certik.com/blog/feg-token-flashloan-exploit-analysis ; Hacken: https://hacken.io/industry-news-and-insights/feg-feed-every-gorilla-exploit-analysis-by-hacken | Cao (không phải bridge, on-chain) | Giải mâu thuẫn: paper xếp off-chain là **sai** (đây là lỗi on-chain). Báo cáo official coi là ứng viên on-chain thì đúng về loại lỗi, nhưng sự cố không thuộc bridge. Metadata ghi `2022-04-28` và mô hình `claimMigrator`/flash loan; không tìm thấy nguồn nào xác nhận. **CẦN NGƯỜI DÙNG XÁC NHẬN.** (Sự cố FEG bridge tháng 12/2024 là một sự cố khác.) |
| pgala | Private key owner của ProxyAdmin pGALA (BSC) bị lộ (SlowMist: lộ trên GitHub; đơn kiện của Gala nêu pNetwork thừa nhận lộ governance key khi deploy). pNetwork gọi đây là "misconfiguration". | Off-chain (quản lý khoá) | **B** | SlowMist, qua ChainCatcher: https://www.chaincatcher.com/ja/article/2082217 ; Benzinga (phía pNetwork gọi là "white-hat"/misconfiguration): https://www.benzinga.com/markets/cryptocurrency/22/11/29564032/gala-token-plunges-20-as-play-to-earn-platform-hacks-itself-as-security-measure ; Cointelegraph (đơn kiện của Gala nêu pNetwork thừa nhận lộ governance key khi deploy): https://cointelegraph.com/news/gamefi-project-gala-files-28m-lawsuit-against-pnetwork | Trung bình | Giải mâu thuẫn: paper xếp on-chain chain nguồn là **không có căn cứ**; các nguồn đều chỉ ra khoá quản trị bị lộ. pNetwork chưa có post-mortem kỹ thuật chính thức. **CẦN NGƯỜI DÙNG XÁC NHẬN.** |
| qubit | `QBridgeETH.deposit` với token native không kiểm `msg.value` nhưng vẫn phát `Deposit(amount)`; relayer mint xQubit trên BSC. | On-chain, chain nguồn (Ethereum) | **A** | KB nội bộ; tham chiếu trong metadata | Cao | Metadata ghi `attack_stage: destination_chain`, trong khi mã lỗi nằm ở chain nguồn. Metadata còn ghi `fork.block_number` 14742532 **lớn hơn** `first_exploit_block` 14180001, tức fork sau thời điểm exploit (không ảnh hưởng chế độ RPC rỗng, nhưng sai cho replay fork). Đề xuất sửa metadata (chưa sửa). Đã có fixture official. |

## Tổng hợp

- **A (tính VER):** nomad, qubit (đã có official); polynetwork, socket (chưa có official spec).
- **B (phòng thủ chiều sâu):** ronin, harmony, multichain, orbit, pgala.
- **C (báo riêng):** wormhole (non-EVM), gempad và fegtoken (không phải bridge; metadata lệch so với nguồn công khai).

## Hệ quả

Nhóm A chỉ có nomad, qubit, polynetwork, socket (socket còn nghi vấn): quá ít để báo cáo VER. Cần bổ sung sự cố bridge on-chain trên EVM từ knowledge base, có đối chiếu nguồn.

## Fixture nhóm A chưa làm trong phiên này

- **polynetwork, socket:** chưa viết `official/` spec và chưa chạy. Phiên này dừng ở Bước 1, nên **không có số liệu official** cho hai fixture này ("—").
- Lưu ý mô hình hoá cho phiên sau: harness official hiện gửi giao dịch tấn công với `msg.value = 0` và chỉ từ một địa chỉ attacker. Fixture PolyNetwork còn cần mô hình hoá bước xác minh chữ ký header của keeper. Đây là quyết định thiết kế cần người dùng duyệt trước khi viết.

## Đề xuất sửa metadata (chưa thực hiện)

- `orbit.incident_date_utc`: `2024-01-01` → `2023-12-31`.
- `qubit.attack_stage`: `destination_chain` → `source_chain`; `qubit.fork.block_number` phải trước `first_exploit_block`.
- `polynetwork.attack_type`: `key_compromise` → lỗi xác minh/whitelist đích on-chain.
- `pgala.attack_stage` đã là `off_chain`, khớp nhóm B.
- `gempad`, `fegtoken`: ngày và root cause cần đối chiếu lại với nguồn.

## Kiểm tra URL nguồn (03/11/2026)

Đã kiểm tra 22 URL trong bảng:
- 15 URL trả về HTTP 200.
- 3 URL bị site chặn client tự động (403/429): Hacken, The Block, CoinDesk. Chưa kiểm chứng được nội dung, nhưng không có dấu hiệu URL sai.
- 3 bài trên `medium.com` (SlowMist, CertiK, GemPad) không truy cập được từ mạng của máy kiểm tra, nhưng có trong chỉ mục tìm kiếm với đúng tiêu đề.
- Đã thay 2 URL: bài usethebitcoin về đơn kiện pGALA đã chết (404/410), thay bằng Cointelegraph; link Benzinga bị cắt cụt, bổ sung đủ đường dẫn.

Bài Benzinga chỉ thuật lại cách pNetwork mô tả sự việc ("white-hat"), không phải bằng chứng lộ khoá. Bằng chứng lộ khoá của pGALA là phân tích của SlowMist (qua ChainCatcher) và nội dung đơn kiện.
