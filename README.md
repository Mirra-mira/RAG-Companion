# KLTN — Hệ thống bộ nhớ dài hạn cho trợ lý ảo hội thoại

Demo hiện thực hoá thiết kế ở Chương 3 của khoá luận: hệ thống trích xuất — lưu
trữ — truy hồi facts người dùng theo thời gian, tích hợp với LLM (Google Gemini)
để tạo phản hồi có ngữ cảnh.

## 1. Yêu cầu môi trường

| Phần mềm | Phiên bản | Ghi chú |
|---|---|---|
| [Docker Desktop](https://www.docker.com/products/docker-desktop) | mới nhất | Đã cài, đang chạy (icon whale ở system tray) |
| Python | 3.10+ | Kiểm tra: `python --version` |
| Google Gemini API key | (tuỳ chọn) | Không có thì chạy chế độ mock — xem mục 4 |

## 2. Chạy demo (3 bước)

### Bước 1 — Khởi động database

Từ thư mục gốc project:
```bash
docker compose up -d
```
- Container `kltn-postgres` dùng image `pgvector/pgvector:pg16`.
- File `database/schema.sql` **tự chạy** trong lần khởi động đầu tiên.
- Verify: `docker compose ps` → cột STATUS hiện `healthy`.

### Bước 2 — Cài backend

```powershell
# Windows PowerShell
cd backend
.\setup.ps1
```
```bash
# Git Bash / macOS / Linux
cd backend
./setup.sh
```
Script tự tạo venv, cài `requirements.txt`, và copy `.env.example` → `.env`.

**Điền API key vào `backend/.env`:**
- Có Gemini key: `GEMINI_API_KEY=<key của bạn>`
- Không có key: sửa `USE_MOCK_LLM=true` (xem mục 4)

### Bước 3 — Chạy backend + mở frontend

```powershell
.\run.ps1        # hoặc ./run.sh
```
- **Backend:** mở `http://localhost:8000/health` → phải trả về `{"status":"ok",...}`
- **Frontend:** mở file `frontend/index.html` bằng trình duyệt (double-click là được, không cần server riêng).

## 3. Test nhanh qua API (không cần frontend)

```bash
# Tạo user
curl -X POST http://localhost:8000/dev/create-user \
  -H "Content-Type: application/json" -d '{"username":"test"}'
# → copy user_id trả về

# Gửi tin nhắn chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"<user_id>","message":"tôi thích phở lắm"}'

# Xem facts đã trích xuất (đợi 1-2s cho write path chạy xong)
curl http://localhost:8000/users/<user_id>/facts
```

> Endpoint `/dev/create-user` chỉ là tiện ích test, **không** nằm trong đặc tả
> API chính thức ở Bảng 3.8 của luận văn.

## 4. Chế độ Mock (không cần API key)

Đặt `USE_MOCK_LLM=true` hoặc để trống `GEMINI_API_KEY` trong `backend/.env`.

- `MockEmbeddingProvider`: chỉ phát hiện REINFORCE khi 2 câu **giống hệt nhau**
  sau chuẩn hoá (bỏ hoa/thường, khoảng trắng). Không phát hiện được tương đồng
  ngữ nghĩa thật (ví dụ "phở" và "phở bò" bị coi là 2 fact khác nhau).
- `MockLLMProvider`: regex đơn giản cho các mẫu tiếng Việt (`thích X`, `mê X`,
  `hết thích X`, `ghét X`).

→ Mock mode chỉ để **kiểm tra luồng** (routing, dedup logic, ranking, cô lập
đa người dùng). Muốn đánh giá chất lượng trích xuất/dedup thật, **bắt buộc**
phải chạy với API key Gemini.

## 5. Dừng hệ thống

```bash
docker compose down       # dừng DB, giữ dữ liệu
docker compose down -v    # dừng + xoá sạch dữ liệu (dùng khi muốn chạy lại schema.sql)
```

## 6. Nâng cấp DB đang chạy (migration)

Nếu bạn đã dựng DB từ trước và **không muốn mất data** (users + facts), chạy các
file trong `database/migrations/` theo thứ tự khi có thay đổi schema:

```bash
docker exec -i kltn-postgres psql -U postgres -d kltn < database/migrations/001_add_conversations.sql
```

- Migration là **idempotent** (chạy nhiều lần không lỗi).
- Nếu không cần giữ data cũ: `docker compose down -v` rồi `docker compose up -d`  — `schema.sql` (đã bao gồm mọi thay đổi) tự chạy lại từ đầu.

## 7. Cấu trúc thư mục

```
kltn-project/
├── docker-compose.yml         # Postgres + pgvector
├── database/
│   ├── schema.sql             # Toàn bộ schema (users, facts, conversations, ...)
│   └── migrations/            # migration script cho DB đang chạy
├── backend/
│   ├── app/
│   │   ├── core/              # config, kết nối DB
│   │   ├── models/            # Pydantic schemas
│   │   ├── repositories/      # IFactRepository, IConversationRepository (DI - mục 2.1.1)
│   │   ├── services/          # Extraction / Dedup / Retrieval / Ranking / Conversation
│   │   ├── controllers/       # API endpoints (Bảng 3.8)
│   │   ├── dependencies.py    # nơi "tiêm" implementation cụ thể vào interface
│   │   └── main.py
│   ├── setup.ps1 / setup.sh   # cài venv + requirements + tạo .env
│   ├── run.ps1  / run.sh      # activate venv + chạy uvicorn
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    └── index.html             # chat UI đơn giản, không cần build tool
```

## 8. Bộ nhớ ngắn hạn hội thoại (ConversationService)

Ngoài bộ nhớ **dài hạn** (facts, mục 3.5), hệ thống có bộ nhớ **ngắn hạn** cho
từng cuộc chat để LLM không mất mạch giữa các lượt:

- Mỗi turn (user + assistant) được lưu vào bảng `conversations`.
- Khi gửi tin nhắn mới, prompt LLM gồm: facts liên quan + `RECENT_TURNS` gần
  nhất + `users.conversation_summary` (tóm tắt các turn xa đã bị nén).
- Khi tổng số turn chưa summarized vượt `SUMMARIZE_THRESHOLD`, service tự
  nén các turn cũ nhất vào `conversation_summary` (background task).

Cấu hình trong `.env` (mặc định đủ dùng):
```
RECENT_TURNS=20             # số turn gần nhất đưa vào prompt
SUMMARIZE_THRESHOLD=30      # vượt ngưỡng này thì trigger tóm tắt
```

## 9. (Phụ lục) Chạy Postgres local thay vì Docker

Chỉ dùng nếu môi trường không hỗ trợ Docker. Không khuyến nghị trên Windows vì
phải cài pgvector thủ công.

```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib build-essential postgresql-server-dev-all git
git clone --branch v0.7.4 https://github.com/pgvector/pgvector.git
cd pgvector && make && sudo make install
sudo -u postgres createdb kltn
sudo -u postgres psql -d kltn -f database/schema.sql
```

Windows: cài PostgreSQL từ postgresql.org, tải
[pgvector release có sẵn](https://github.com/pgvector/pgvector#installation),
dùng pgAdmin tạo DB `kltn` và chạy `database/schema.sql`. Sau đó sửa
`DATABASE_URL` trong `backend/.env` cho khớp user/password của bạn.
