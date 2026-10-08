import os
import logging
from typing import Any, Optional, List, Dict
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

TURSO_URL = os.getenv("TURSO_DATABASE_URL", "").strip()
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "").strip()

if TURSO_URL.startswith("libsql://"):
    TURSO_URL = TURSO_URL.replace("libsql://", "https://")

# В тестах всегда используем локальный SQLite, чтобы тесты летали и не трогали прод-базу
IS_TESTING = bool(os.getenv("TESTING") or os.getenv("PYTEST_CURRENT_TEST"))
USE_TURSO = bool(TURSO_URL and TURSO_TOKEN and not IS_TESTING)

if USE_TURSO:
    import libsql_client
    logger.info("Turso Cloud SQLite enabled (%s)", TURSO_URL)
else:
    import aiosqlite
    logger.info("Local SQLite (aiosqlite) enabled")

class TursoRowCompat:
    """Обертка над строкой Turso, эмулирующая aiosqlite.Row"""
    def __init__(self, row):
        self._row = row
        self._dict = row.asdict() if hasattr(row, 'asdict') else {}

    def __getitem__(self, item):
        return self._row[item]

    def __iter__(self):
        return iter(self._row)

    def __len__(self):
        return len(self._row)

    def keys(self):
        return self._dict.keys()

    def values(self):
        return self._dict.values()

    def items(self):
        return self._dict.items()

    def get(self, key, default=None):
        return self._dict.get(key, default)

    def asdict(self):
        return self._dict

    def __repr__(self):
        return repr(self._dict)

class TursoCursorCompat:
    """Обертка над курсором для совместимости с aiosqlite"""
    def __init__(self, result_set):
        self._raw_rows = result_set.rows if result_set else []
        self._rows = [TursoRowCompat(r) for r in self._raw_rows]
        self._idx = 0
        self.lastrowid = getattr(result_set, 'last_insert_rowid', None)
        self.rowcount = getattr(result_set, 'rows_affected', len(self._rows))

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def fetchone(self):
        if self._idx < len(self._rows):
            row = self._rows[self._idx]
            self._idx += 1
            return row
        return None

    async def fetchall(self):
        remaining = self._rows[self._idx:]
        self._idx = len(self._rows)
        return remaining

class TursoQueryContext:
    """Позволяет использовать как await db.execute(...), так и async with db.execute(...)"""
    def __init__(self, coro):
        self._coro = coro
        self._cursor = None

    def __await__(self):
        return self._coro.__await__()

    async def __aenter__(self):
        self._cursor = await self._coro
        return self._cursor

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

class TursoConnectionCompat:
    """Эмулятор aiosqlite.Connection для Turso Cloud"""
    def __init__(self, url: str, token: str):
        self._url = url
        self._token = token
        self._client: Optional[libsql_client.Client] = None
        self.row_factory = None

    async def __aenter__(self):
        self._client = libsql_client.create_client(self._url, auth_token=self._token)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.close()
            self._client = None

    async def _do_execute(self, sql: str, params: Any = None):
        if not self._client:
            self._client = libsql_client.create_client(self._url, auth_token=self._token)
            
        # Игнорируем только PRAGMA настройки файла (WAL, synchronous, cache_size и т.д.)
        # Но оставляем интроспекцию (например, PRAGMA table_info(...))
        sql_upper = sql.strip().upper()
        if any(sql_upper.startswith(p) for p in [
            "PRAGMA JOURNAL_MODE", "PRAGMA SYNCHRONOUS", "PRAGMA BUSY_TIMEOUT",
            "PRAGMA CACHE_SIZE", "PRAGMA TEMP_STORE"
        ]):
            class DummyResult:
                rows = []
                last_insert_rowid = None
                rows_affected = 0
            return TursoCursorCompat(DummyResult())

        if params is None:
            p = []
        elif isinstance(params, (tuple, list)):
            p = list(params)
        elif isinstance(params, dict):
            p = params
        else:
            p = [params]
            
        try:
            res = await self._client.execute(sql, p)
            return TursoCursorCompat(res)
        except KeyError as e:
            # Ошибка базы данных через Turso HTTP API (возвращает 'error' вместо 'result')
            import aiosqlite
            raise aiosqlite.OperationalError(f"Turso SQL error on query: {sql[:100]}") from e

    def execute(self, sql: str, params: Any = None):
        return TursoQueryContext(self._do_execute(sql, params))

    async def executemany(self, sql: str, params_list: List[Any]):
        if not self._client:
            self._client = libsql_client.create_client(self._url, auth_token=self._token)
        statements = [
            libsql_client.Statement(sql, list(p) if isinstance(p, (tuple, list)) else p)
            for p in params_list
        ]
        return await self._client.batch(statements)

    async def commit(self):
        # В Turso HTTP каждый запрос атомарен
        pass

    async def rollback(self):
        pass

    async def close(self):
        if self._client:
            await self._client.close()
            self._client = None

def connect(database: str = "", **kwargs):
    """Фабрика подключений: Turso Cloud или локальный aiosqlite"""
    if USE_TURSO:
        return TursoConnectionCompat(TURSO_URL, TURSO_TOKEN)
    import aiosqlite
    return aiosqlite.connect(database, **kwargs)

def patch_aiosqlite_if_turso():
    """Автоматически перенаправляет aiosqlite.connect на Turso Cloud, если активен Turso"""
    if USE_TURSO:
        import aiosqlite
        aiosqlite.connect = connect
        logger.info("aiosqlite.connect redirected to Turso Cloud")

patch_aiosqlite_if_turso()

Row = TursoRowCompat if USE_TURSO else (aiosqlite.Row if not USE_TURSO else None)
