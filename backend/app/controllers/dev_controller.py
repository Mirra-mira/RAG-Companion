"""Endpoint TIỆN ÍCH cho việc test local — KHÔNG thuộc đặc tả API chính thức
ở Bảng 3.8 (vốn giả định user đã tồn tại qua hệ thống đăng ký/xác thực riêng,
nằm ngoài phạm vi khóa luận). Chỉ dùng để tạo user nhanh khi demo/test.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.db import get_conn

router = APIRouter(prefix="/dev", tags=["dev-only"])


class CreateUserRequest(BaseModel):
    username: str


@router.post("/create-user")
def create_user(req: CreateUserRequest):
    with get_conn() as conn:
        row = conn.execute(
            "INSERT INTO users (username) VALUES (%s) RETURNING user_id",
            (req.username,),
        ).fetchone()
        conn.commit()
        return {"user_id": str(row[0]), "username": req.username}


@router.get("/users")
def list_users():
    """Liet ke tat ca user trong DB. Dung cho frontend demo — de UI dong bo
    duoc danh sach user giua nhieu trinh duyet / profile, thay vi chi doc
    tu localStorage cua browser."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT user_id, username, created_at FROM users ORDER BY created_at ASC"
        ).fetchall()
        return [
            {"user_id": str(r[0]), "username": r[1], "created_at": r[2].isoformat()}
            for r in rows
        ]
