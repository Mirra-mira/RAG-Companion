from psycopg_pool import ConnectionPool
from pgvector.psycopg import register_vector
from app.core.config import settings

pool = ConnectionPool(
    conninfo=settings.DATABASE_URL,
    min_size=1,
    max_size=10,
    open=True,
    configure=lambda conn: register_vector(conn),
)


def get_conn():
    """Dependency dùng trong FastAPI: with get_conn() as conn: ..."""
    return pool.connection()
