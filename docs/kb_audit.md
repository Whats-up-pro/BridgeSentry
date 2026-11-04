# Kiểm toán knowledge base (48 record)

**Trạng thái:** đề xuất, chưa được tác giả duyệt. Tài liệu này **không sửa** bất kỳ file nào trong `src/module2_rag/data/`. Người dùng duyệt các đề xuất ở cuối trước khi sửa.

**Phạm vi:** 48 file JSON trong `src/module2_rag/data/`. Mỗi record được đối chiếu các trường `bridge`, `date`, `loss_usd`, `chains`, `vulnerability_class`, `attack_stage`, `root_cause`/`summary`, `attack_trace` với post-mortem chính thức hoặc phân tích của hãng bảo mật, tìm bản trùng/alias, và kết luận theo một trong bốn mức: **ĐÚNG**, **SAI MỘT PHẦN** (ghi trường sai + giá trị đúng), **KHÔNG XÁC NHẬN ĐƯỢC**, **TRÙNG** (với record nào).

## Giới hạn phương pháp (đọc trước)

- **Không mở được trang nguồn trực tiếp trong phiên này.** Chính sách mạng của session chỉ cho phép công cụ *tìm kiếm* web (WebSearch); `WebFetch`/`curl` tới `halborn.com`, `certik.com`, `medium.com`, `blocksec.com`, ... đều bị chặn (ENOTFOUND / egress rejected). Vì vậy việc đối chiếu dựa trên **tóm tắt chỉ mục tìm kiếm** của các bài đó + kiến thức sự cố đã công bố + tính nhất quán nội tại của record, **không phải** đọc toàn văn.
- **Không kiểm được "URL còn sống" bằng máy** vì lý do trên. Các URL nghi chết được đánh dấu theo nguồn thứ cấp/khóa (xem cột Ghi chú). Record `fegtoken_20240220` trích một tweet (`twitter.com/fegtoken/status/1760145290837270753`) mà đề bài đã xác nhận trả 404.
- "Mức chắc chắn" trong cột Ghi chú phản ánh giới hạn trên.

## Cấu trúc alias trong KB

Ngoài các record `source: "curated"` (chi tiết, là bản gốc), KB còn chứa hai lớp record **thưa, không có số liệu**, chỉ trỏ về cùng post-mortem — chúng là **alias/trùng** của record curated tương ứng:

- **`*_xscope.json` (`source: "xscope_ase22"`, 12 file):** nhãn từ catalog XScope (ASE'22). Không có `date`/`loss_usd`/`chains`. Nhiều record còn gán `vulnerability_class`/`attack_stage` **mâu thuẫn** với record curated (ví dụ Wormhole/PolyNetwork/Synapse bị gán `fake_deposit` dù bản chất khác hẳn).
- **`smartaxe_fse24` (5 file):** nhãn thủ công từ SmartAxe (FSE'24). Không có `loss_usd`/`chains`/`references`, `summary` chỉ ghi "manually-labeled ... attack on <bridge>".

Các cụm trùng:

| Sự cố | Bản curated gốc | Alias trùng |
| --- | --- | --- |
| Qubit/QBridge (01/2022) | `qubit_20220127` | `qbridge_20220128` (smartaxe), `qubit_bridge_xscope` |
| Meter.io Passport (02/2022) | `meterio_20220205` | `metpassport_20220206` (curated!), `meterpassport_20220206` (smartaxe), `meter_io_xscope` |
| Anyswap V3 (07/2021) | `anyswap_20210710` | `anyswap_xscope` |
| Multichain "without permit" (01/2022) | `multichain_20220118` | `multichain_xscope` |
| pNetwork pBTC-on-BSC (09/2021) | `pnetwork_20210919` | `pnetwork_20210920` (smartaxe), `pnetwork_xscope` |
| PolyNetwork (08/2021) | `polynetwork_20210810` | `polynetwork_xscope` |
| Ronin (03/2022) | `ronin_20220323` | `ronin_xscope` |
| Synapse metapool (11/2021) | `synapse_20211109` | `synapse_20211106` (smartaxe), `synapse_bridge_xscope` |
| Wormhole (02/2022) | `wormhole_20220202` | `wormhole_xscope` |
| THORChain ETH router (06/2021) | `thorchain_20210629` | `thorchain_1_xscope` |
| THORChain 07/15/2021 | `thorchain_20210716` | `thorchain_2_xscope` |
| THORChain 07/22/2021 | `thorchain_20210723` | `thorchain_3_xscope` |

## Bảng 48 dòng

Cột **Trùng** ghi record gốc nếu dòng là alias. Cột **Verdict**: ĐÚNG / SAI MỘT PHẦN / KXN (không xác nhận được) / TRÙNG.

| # | File | Bridge | Date | Loss (USD) | class / stage | Verdict | Ghi chú (trường sai → đúng; mức chắc chắn) |
|---|---|---|---|---|---|---|---|
| 1 | anyswap_20210710 | Anyswap (Multichain V3) | 2021-07-10 | 7,900,000 | key_compromise / off_chain | ĐÚNG | Lặp giá trị R/nonce trong ký ECDSA làm lộ shard khoá MPC. Khớp statement Multichain. Cao. |
| 2 | anyswap_xscope | Anyswap | — | — | fake_deposit / destination_chain | TRÙNG | Trùng #1. **class `fake_deposit` mâu thuẫn** với bản chất lộ khoá (key_compromise). |
| 3 | bnbbridge_20221007 | BNB Token Hub | 2022-10-07 | 586,000,000 | fake_deposit / destination_chain | ĐÚNG | Lỗi xác minh Merkle/IAVL cho phép proof giả; ~2M BNB bị mint. Khớp BlockSec. Cao. |
| 4 | bridgemutual_20220507 | Bridge Mutual | 2022-05-07 | 2,400,000 | oracle_manipulation / source_chain | KXN | Không tìm được sự cố Bridge Mutual ngày 07/05/2022. Bridge Mutual là giao thức **bảo hiểm**, không phải cross-chain bridge → có thể không thuộc phạm vi KB. Thấp. |
| 5 | chainswap_20210711 | ChainSwap | 2021-07-11 | 8,000,000 | signature_forgery / off_chain | SAI MỘT PHẦN | Sự cố ChainSwap 10–11/07/2021 (~$8M) có thật. **`attack_stage: off_chain` → on-chain**: lỗi là kiểm chữ ký/uỷ quyền mint **trên hợp đồng**, không phải off-chain. Chi tiết "ecrecover trả address(0)" chưa đối chiếu được. Trung bình. |
| 6 | evodefi_20220607 | EvoDeFi | 2022-06-07 | 6,000,000 | key_compromise / off_chain | KXN | Nguồn công khai mô tả EvoDeFi là **mất khả năng chi trả / nghi chiếm dụng của vận hành** (~$45.5M, tài sản bắc cầu thiếu bảo chứng + mất vốn trên Anchor/Terra), ~05/2022 — **không** phải "exploit relayer một chữ ký" $6M ngày 07/06. Cơ chế, loss và date đều không khớp. Thấp. |
| 7 | fegtoken_20240220 | FEGtoken | 2024-02-20 | 900,000 | key_compromise / off_chain | KXN | Đề bài đã xác nhận: tweet trích dẫn trả 404; không nguồn nào xác nhận sự cố FEG lộ khoá 20/02/2024. Sự cố FEG thật: flash loan FEGexPRO (05/2022, lỗi DEX) và FEG SmartBridge (29/12/2024, xem fixture `feg_bridge_2024`). |
| 8 | gempad_20240419 | GemPad | 2024-04-19 | 1,900,000 | fake_deposit / destination_chain | SAI MỘT PHẦN | Sự cố GemPad thật: **reentrancy trong Locker V2, 17/12/2024**, ~$1.9M, trên ETH/BSC/Base/Polygon — và **GemPad là nền tảng khoá token, không phải bridge**. KB sai `date` (→ 2024-12-17), `root_cause` ("lock không kiểm chủ sở hữu" → reentrancy), `class`/`attack_stage`. Đề nghị loại khỏi KB bridge. |
| 9 | harmony_horizon_20220624 | Harmony Horizon | 2022-06-24 | 100,000,000 | key_compromise / off_chain | SAI MỘT PHẦN | Đúng sự cố/loss/class. **Ngưỡng multisig: KB ghi "2/4" → đúng là 2-of-5** (2/5 khoá bị chiếm). Cao. |
| 10 | lifinance_20220320 | Li.Finance | 2022-03-20 | 600,000 | logic_bug / source_chain | ĐÚNG | `swapAndStartBridge` gọi low-level tuỳ ý, không whitelist target/DEX. Khớp blog Li.Finance. Cao. |
| 11 | meter_io_xscope | meter.io | — | — | fake_deposit / destination_chain | TRÙNG | Trùng #12. class `fake_deposit`/stage `destination_chain` lệch với bản curated (logic_bug/source_chain). |
| 12 | meterio_20220205 | meter.io | 2022-02-05 | 4,400,000 | logic_bug / source_chain | SAI MỘT PHẦN | **Bản gốc của cụm Meter.** Root cause (handler lẫn `msg.value` native với `amount`) đúng. **`chains: [ethereum, bsc]`** chưa chuẩn: sự cố Meter Passport thực tế trên **BSC ↔ Moonriver** (meterBNB). Trung bình-cao. |
| 13 | meterpassport_20220206 | Meter Passport | 2022-02-06 | — | logic_bug / source_chain | TRÙNG | Trùng #12 (smartaxe, cùng sự cố, lệch 1 ngày, không có loss). |
| 14 | metpassport_20220206 | MeterPassPort | 2022-02-06 | 4,400,000 | logic_bug / source_chain | TRÙNG | Trùng #12 (curated, cùng sự cố, lệch 1 ngày). `root_cause` "depositETH thiếu require(msg.value==amount)" cùng lỗi với #12. |
| 15 | multichain_20220118 | Multichain | 2022-01-18 | 3,000,000 | signature_forgery / destination_chain | ĐÚNG | Lỗi "without permit" (permit không ràng buộc token mục tiêu). Khớp Zengo. Ghi chú: bản chất gần "thiếu kiểm permit" hơn là "forgery". Cao. |
| 16 | multichain_20230215 | Multichain | 2023-02-15 | — | key_compromise / off_chain | KXN | Không có sự cố Multichain riêng ngày 15/02/2023 được xác nhận; vụ lớn là **MPC bị chiếm 07/2023** (xem #17). Nhiều khả năng là nhãn trùng/mốc không chuẩn của saga 2023 (smartaxe, không loss/chains). Thấp. |
| 17 | multichain_20230715 | Multichain | 2023-07-15 | 126,000,000 | key_compromise / off_chain | ĐÚNG | Chiếm giữ/mất kiểm soát khoá MPC sau khi CEO bị bắt; rút ~$126M+. Cao. |
| 18 | multichain_xscope | MultiChain | — | — | signature_forgery / destination_chain | TRÙNG | Trùng #15 (cùng URL Zengo "without permit"). |
| 19 | nerve_20211115 | Nerve Bridge | 2021-11-15 | 1,000,000 | oracle_manipulation / source_chain | KXN | Chưa đối chiếu được sự cố Nerve ~$1M 15/11/2021 (thao túng `virtual_price`). Nerve là stableswap kiểu Curve trên BSC; liên hệ "bridge" không rõ. Thấp. |
| 20 | nomad_20220801 | Nomad | 2022-08-01 | 190,000,000 | fake_deposit / destination_chain | ĐÚNG | `Replica.initialize` pre-approve root 0x00 → `acceptableRoot(0x00)`. Khớp RCA Nomad (đã có fixture official). Cao. |
| 21 | orbit_20240101 | Orbit Bridge | 2024-01-01 | 82,000,000 | key_compromise / off_chain | SAI MỘT PHẦN | **`date` → 2023-12-31** (thông báo Orbit: 31/12/2023 20:52:47 UTC; đã nêu trong `official_fixture_classification.md`). Loss/class hợp lý. Cao (ngày). |
| 22 | pgala_20221103 | pGALA | 2022-11-03 | 10,000,000 | key_compromise / source_chain | SAI MỘT PHẦN | **`attack_stage: source_chain` → off_chain** (sự cố là khoá quản trị/cấu hình custodian, không phải lỗi hợp đồng on-chain; nhất quán với nhóm B trong classification doc). Loss là ước tính thô (lượng pGALA mint rất lớn). Trung bình. |
| 23 | pnetwork_20210919 | pNetwork | 2021-09-19 | 12,000,000 | logic_bug / off_chain | ĐÚNG | Node pNetwork bỏ kiểm input UTXO cho pegout pBTC-on-BSC → replay. ~$12M. Trung bình-cao. |
| 24 | pnetwork_20210920 | pNetwork | 2021-09-20 | — | logic_bug / off_chain | TRÙNG | Trùng #23 (smartaxe, lệch 1 ngày). |
| 25 | pnetwork_xscope | pNetwork | — | — | fake_deposit / destination_chain | TRÙNG | Trùng #23. class/stage lệch với bản curated. |
| 26 | polynetwork_20210810 | PolyNetwork | 2021-08-10 | 611,000,000 | key_compromise / off_chain | SAI MỘT PHẦN | `root_cause` ("ECCM gọi ECCD với msg.sender=manager, đổi keeper không kiểm") **đúng**, nhưng **`class: key_compromise` và `attack_stage: off_chain` SAI**: không khoá nào bị lộ; đây là **lỗi logic on-chain** (bypass xác minh/đổi keeper) — nên là on-chain (chain thực thi thông điệp). Khớp fixture `polynetwork`. Cao. |
| 27 | polynetwork_xscope | Polynetwork | — | — | fake_deposit / destination_chain | TRÙNG | Trùng #26. class `fake_deposit` sai. |
| 28 | qanxbridge_20220518 | QANX Bridge | 2022-05-18 | 1,900,000 | key_compromise / off_chain | ĐÚNG | Ví bridge QANX dùng 1 EOA; ~$1.9M 05/2022. Khớp mô tả, nhưng nguồn ít phổ biến. Thấp-trung bình. |
| 29 | qbridge_20220128 | Qubit Bridge | 2022-01-28 | — | fake_deposit / destination_chain | TRÙNG | Trùng #30 (smartaxe; QBridge là bridge của Qubit; lệch 1 ngày). |
| 30 | qubit_20220127 | Qubit Finance | 2022-01-27 | 80,000,000 | fake_deposit / destination_chain | ĐÚNG | `deposit()` nhận native sentinel không kiểm `msg.value`; mint xETH không bảo chứng. Khớp (đã có fixture official). Cao. |
| 31 | qubit_bridge_xscope | Qubit Bridge | — | — | fake_deposit / destination_chain | TRÙNG | Trùng #30. |
| 32 | rainbow_20220505 | Rainbow Bridge | 2022-05-05 | 0 | fake_deposit / off_chain | ĐÚNG | Lần thử **thất bại** (watcher/challenger hoạt động), loss=0; Aurora tịch thu bond. Cao. |
| 33 | ronin_20220323 | Ronin Network | 2022-03-23 | 624,000,000 | key_compromise / off_chain | ĐÚNG | **Ronin 03/2022** (5/9 khoá validator bị chiếm) — nhóm B, **khác** sự cố Ronin 08/2024 (bỏ `initializeV3`, xem fixture `ronin_2024`). ~$625M. Cao. |
| 34 | ronin_xscope | Ronin | — | — | key_compromise / off_chain | TRÙNG | Trùng #33. |
| 35 | rubic_20221225 | Rubic | 2022-12-25 | 1,400,000 | logic_bug / source_chain | ĐÚNG | Giống Li.Finance: định tuyến gọi ngoài không kiểm target. ~$1.4M 12/2022. Cao. |
| 36 | socket_20240116 | Socket Gateway | 2024-01-16 | 3,300,000 | logic_bug / source_chain | ĐÚNG | Route không hoạt động vẫn qua validator / `swapExtraData` không kiểm → chèn `transferFrom` trên approval. Khớp. (Classification doc loại Socket khỏi benchmark official vì **đơn chain**, nhưng record KB thì chính xác.) Cao. |
| 37 | synapse_20211106 | Synapse Bridge | 2021-11-06 | — | logic_bug / source_chain | TRÙNG | Trùng #38 (smartaxe, lệch ngày; cùng sự cố metapool 11/2021). |
| 38 | synapse_20211109 | Synapse Bridge | 2021-11-09 | 8,000,000 | logic_bug / source_chain | SAI MỘT PHẦN | Sự cố metapool Synapse 11/2021 (giá `virtual_price` pre/post-fee). **Date lệch URL** (post-mortem ghi 11-06; field ghi 11-09). Là lỗi AMM metapool (liên quan bridge), phần lớn được whitehat cứu. Trung bình. |
| 39 | synapse_bridge_xscope | Synapse Bridge | — | — | fake_deposit / destination_chain | TRÙNG | Trùng #38. class `fake_deposit` sai (thực tế là lỗi định giá metapool). |
| 40 | thorchain_1_xscope | THORChain #1 | — | — | logic_bug / destination_chain | TRÙNG | Trùng #42 (cùng URL "eth-parsing-error-and-exploit"). |
| 41 | thorchain_20210628 | THORChain | 2021-06-28 | 140,000 | logic_bug / source_chain | SAI MỘT PHẦN | **Date lệch URL** (bài ghi "29-jun-21"). Sự cố router BEP20/ETH cuối 06/2021. Trung bình. |
| 42 | thorchain_20210629 | THORChain | 2021-06-29 | 350,000 | logic_bug / source_chain | ĐÚNG | ETH router `transferOut` xử lý memo lỗi. Trung bình-cao. |
| 43 | thorchain_20210716 | THORChain | 2021-07-16 | 5,000,000 | logic_bug / source_chain | SAI MỘT PHẦN | **Date lệch URL** (notion ghi 07-15). ETH router lẫn đường native/ERC-20, ~$5M. Trung bình. |
| 44 | thorchain_20210723 | THORChain | 2021-07-23 | 8,000,000 | logic_bug / source_chain | SAI MỘT PHẦN | **Date lệch URL** (notion ghi 07-22). Memo không khớp symbol tài sản, ~$8M. Trung bình. |
| 45 | thorchain_2_xscope | THORChain #2 | — | — | fake_deposit / destination_chain | TRÙNG | Trùng #43 (URL 07-15). class `fake_deposit` sai. |
| 46 | thorchain_3_xscope | THORChain #3 | — | — | fake_deposit / destination_chain | TRÙNG | Trùng #44 (URL 07-22). class `fake_deposit` sai. |
| 47 | wormhole_20220202 | Wormhole | 2022-02-02 | 326,000,000 | signature_forgery / destination_chain | ĐÚNG | Chương trình Solana không kiểm sysvar instructions → chữ ký guardian giả, mint whETH. ~$326M. Cao. |
| 48 | wormhole_xscope | Wormhole | — | — | fake_deposit / destination_chain | TRÙNG | Trùng #47. **class `fake_deposit` sai** (thực tế là bypass xác minh chữ ký). |

## Tổng hợp

- **TRÙNG (18):** #2, 11, 13, 14, 18, 24, 25, 27, 29, 31, 34, 37, 39, 40, 45, 46, 48 (17 alias) **+ #14 `metpassport_20220206`** là trùng *curated–curated* với #12. Gồm 12 record `*_xscope`, 4 record `smartaxe` (meterpassport, pnetwork_20210920, qbridge_20220128, synapse_20211106) và 1 curated (metpassport). Nhiều alias còn gán `vulnerability_class`/`attack_stage` mâu thuẫn với bản gốc.
- **KHÔNG XÁC NHẬN ĐƯỢC (5):** #4 bridgemutual, #6 evodefi, #7 fegtoken, #16 multichain_20230215, #19 nerve. (Thêm #28 qanxbridge ở mức thấp-trung bình — tạm xếp ĐÚNG nhưng cần nguồn mạnh hơn.)
- **SAI MỘT PHẦN (11):** #5 chainswap (stage), #8 gempad (date/root_cause/class + không phải bridge), #9 harmony (ngưỡng 2/4→2/5), #12 meterio (chains), #21 orbit (date), #22 pgala (stage), #26 polynetwork (class/stage), #38 synapse (date), #41/#43/#44 thorchain (date lệch URL).
- **ĐÚNG (còn lại ~14):** #1 anyswap, #3 bnbbridge, #10 lifinance, #15 multichain_20220118, #17 multichain_20230715, #20 nomad, #23 pnetwork, #28 qanxbridge (thấp), #30 qubit, #32 rainbow, #33 ronin, #35 rubic, #36 socket, #42 thorchain_20210629, #47 wormhole.

Hai record đề bài nêu sẵn được xác nhận: **`gempad_20240419` sai** (sự cố thật là reentrancy locker 17/12/2024, không phải bridge) và **`fegtoken_20240220` không xác nhận được** (tweet 404).

## Đề xuất sửa (CHƯA thực hiện — chờ người dùng duyệt)

> Không file nào trong `src/module2_rag/data/` bị sửa. Dưới đây là đề xuất để người dùng quyết định.

**Loại khỏi KB bridge (hoặc đánh dấu không phải bridge / không xác nhận):**
- `gempad_20240419` — không phải bridge; mọi trường lệch sự cố thật.
- `fegtoken_20240220` — không nguồn xác nhận; nguồn trích 404.
- `bridgemutual_20220507` — giao thức bảo hiểm, không phải cross-chain bridge; không có sự cố ngày này.
- `evodefi_20220607` — mô tả "exploit relayer 1 chữ ký" không khớp nguồn (mất khả năng chi trả/chiếm dụng); loss/date nghi sai.
- `nerve_20211115`, `multichain_20230215` — chưa đối chiếu được; cần nguồn hoặc loại.

**Khử trùng (gộp hoặc đánh dấu alias, giữ 1 bản gốc mỗi cụm):**
- Giữ `qubit_20220127`; đánh dấu `qbridge_20220128`, `qubit_bridge_xscope` là alias.
- Giữ `meterio_20220205`; đánh dấu `metpassport_20220206`, `meterpassport_20220206`, `meter_io_xscope` là alias (và sửa `chains`→ bsc/moonriver).
- Tương tự cho các cụm anyswap, multichain(0118), pnetwork, polynetwork, ronin, synapse, wormhole, thorchain (xem bảng cụm ở trên).
- Với mọi alias `*_xscope`/`smartaxe` có `vulnerability_class`/`attack_stage` mâu thuẫn, **đồng bộ theo bản curated** (đặc biệt bỏ nhãn `fake_deposit` sai ở wormhole/polynetwork/synapse/pnetwork/anyswop xscope).

**Sửa trường (record ĐÚNG/SAI MỘT PHẦN, giữ lại):**
- `harmony_horizon_20220624`: ngưỡng multisig 2/4 → **2/5**.
- `orbit_20240101`: `date` 2024-01-01 → **2023-12-31**.
- `pgala_20221103`: `attack_stage` source_chain → **off_chain**.
- `polynetwork_20210810`: `vulnerability_class` key_compromise → **verification_bypass/logic_bug**; `attack_stage` off_chain → **on-chain (chain thực thi thông điệp)**.
- `chainswap_20210711`: `attack_stage` off_chain → **on-chain (source/dest)**.
- `meterio_20220205`: `chains` [ethereum,bsc] → **[bsc, moonriver]** (cần xác nhận lại).
- `synapse_20211109`, `thorchain_20210628/20210716/20210723`: rà lại `date` cho khớp ngày giao dịch đầu tiên theo post-mortem (lệch 1 ngày/UTC).

**Trước khi chạy holdout:** nên khử trùng (18 record) để tránh rò rỉ/đếm trùng, và loại/đánh dấu 5 record không xác nhận được. Mọi thay đổi cần một lần đối chiếu đọc-toàn-văn nguồn (phiên này bị chặn fetch, chỉ đối chiếu qua tóm tắt tìm kiếm).
