# Dataset thực nghiệm — schema & định nghĩa chỉ số

Mỗi file `uXX.json` = 1 user giả lập (1 chuỗi hội thoại). Xem `sample_u01.json`.

## Schema
- `turns[]`: các tin nhắn của USER (`t`, `text`). Write path chỉ dùng tin nhắn user.
- `facts[]`: gold fact mà một bộ trích xuất lý tưởng sẽ lấy ra:
  - `key` (định danh), `turn`, `category`, `content` (đã lowercase, như ExtractionService xuất)
  - `action`: ADD | REINFORCE | CONFLICT (gold cho DedupService)
  - `target`: key bị gộp/bị thay thế (với REINFORCE/CONFLICT)
  - Turn không có fact nào => không xuất hiện trong `facts` (gold = NOOP)
- `queries[]`: câu hỏi đặt sau khi đã nạp tới `after_turn`
  - `type`: direct | paraphrase | conflict | duplicate | no_relevant
  - `relevant`: key các fact cần truy hồi được
  - `stale`: key các fact đã bị thay thế, KHÔNG được xuất hiện
  - `answer_keywords`: từ khoá phải có trong câu trả lời (cho end-to-end)

## 3 track đánh giá (tách riêng để không nhiễu lẫn nhau)
- **Track A — Retrieval & Dedup (chính):** BỎ QUA extraction, nạp thẳng `facts` đã gán nhãn
  vào pipeline qua `dedup.process()`, ghi lại `fact_id -> key`. Nhờ đó mọi row truy hồi
  được map về gold key chính xác, không phụ thuộc chất lượng LLM trích xuất.
- **Track B — Extraction:** chạy `extract()` trên `turns`, so với `facts` (khớp bằng
  cosine embedding >= ngưỡng hoặc LLM judge) -> P/R/F1.
- **Track C — End-to-end:** hỏi `queries`, kiểm tra `answer_keywords` (+ LLM judge nếu cần).

## Chỉ số (Track A, tại k = RANK_TOP_K)
Key chuẩn của 1 row = `target` nếu action là REINFORCE, ngược lại là `key`.
- **Precision@k** = (#row relevant) / (#row trả về); **Recall@k** = (#key relevant được tìm thấy) / (#relevant)
- **MRR**: nghịch đảo hạng của row relevant đầu tiên
- **Stale@k** = #row thuộc `stale` / #row trả về (điểm yếu của vector thuần khi có mâu thuẫn)
- **Redundancy@k** = 1 - (#key phân biệt / #row trả về) (trùng lặp chiếm slot)
- **Dedup accuracy** + confusion matrix 4x4 (ADD/REINFORCE/CONFLICT/NOOP)
- Query `no_relevant`: báo riêng **false-positive rate** (có trả fact nào không), vì P/R vô nghĩa
- Báo cáo theo từng `type` để thấy baseline nào yếu ở đâu
