# AnyShare 性能优化方案 A 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 数据库连接复用 + WAL 模式 + 索引 + 静态资源缓存，页面响应提升 30-50%，并发能力提升 2-3 倍。

**Architecture:** 在 `database_service.py` 顶层新增 `threading.local()` 和 `get_conn()`，所有数据访问函数不再各自 `connect()`/`close()`，改为复用线程本地连接。`init_db()` 新增 4 个索引。`routes.py` 的 `server_static` 根据文件后缀设置 `Cache-Control` 头。

**Tech Stack:** Python 3.13, SQLite3, Bottle, Waitress

---

### Task 1: 新增 `get_conn()` 连接复用入口

**Files:**
- Modify: `services/database_service.py:1-9`

- [ ] **Step 1: 在 import 区域后添加 `threading` 导入和 `get_conn()` 函数**

在 `import sqlite3` 之后（第 4 行附近）插入：

```python
import threading

_local = threading.local()


def get_conn() -> sqlite3.Connection:
    """返回当前线程复用的数据库连接，首次调用时启用 WAL 模式。"""
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
    return _local.conn
```

- [ ] **Step 2: 验证语法**

Run: `uv run python -c "from services.database_service import get_conn; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add services/database_service.py
git commit -m "feat: add get_conn() with thread-local connection and WAL mode"
```

---

### Task 2: 重构所有数据访问函数使用 `get_conn()`

**Files:**
- Modify: `services/database_service.py:31-779`

**模式：** 每个函数中删除 `conn = sqlite3.connect(...)`、`conn.row_factory = ...`、`conn.close()` 三行，替换为 `conn = get_conn()`。

- [ ] **Step 1: `init_db()` — 保持不变**

`init_db()` 在启动时调用，不在请求线程内，保留独立连接。但需要追加索引创建（见 Task 3）。

- [ ] **Step 2: `add_file()` — 修改**

```python
# 原来（第 143-171 行）:
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    ...
    conn.commit()
    conn.close()

# 改为:
    conn = get_conn()
    cursor = conn.cursor()
    ...
    conn.commit()
```

- [ ] **Step 3: `get_user_files()` — 修改**

```python
# 原来:
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    ...
    conn.close()

# 改为:
    conn = get_conn()
    cursor = conn.cursor()
    ...
```

- [ ] **Step 4: `get_file()` — 修改**

```python
# 原来:
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    ...
    conn.close()

# 改为:
    conn = get_conn()
    cursor = conn.cursor()
    ...
```

- [ ] **Step 5: `delete_expired_files()` — 修改**

注意：此函数在 cleanup 线程中运行，`threading.local()` 会给它独立的连接，行为正确。

```python
# 原来:
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    ...
    conn.commit()
    conn.close()

# 改为:
    conn = get_conn()
    cursor = conn.cursor()
    ...
    conn.commit()
```

- [ ] **Step 6: `delete_file_from_db()` — 修改**

```python
# 原来:
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    ...
    conn.commit()
    conn.close()

# 改为:
    conn = get_conn()
    cursor = conn.cursor()
    ...
    conn.commit()
```

- [ ] **Step 7: `add_user()` — 修改**

```python
# 原来:
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    ...
    conn.close()

# 改为:
    conn = get_conn()
    cursor = conn.cursor()
    ...
```

- [ ] **Step 8: `get_user()` — 修改**

```python
# 原来:
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    ...
    conn.close()

# 改为:
    conn = get_conn()
    cursor = conn.cursor()
    ...
```

- [ ] **Step 9: `get_all_users()` — 修改**

```python
# 原来:
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    ...
    conn.close()

# 改为:
    conn = get_conn()
    cursor = conn.cursor()
    ...
```

- [ ] **Step 10: `delete_user()` — 修改**

```python
# 原来:
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    ...
    conn.close()

# 改为:
    conn = get_conn()
    cursor = conn.cursor()
    ...
```

- [ ] **Step 11: `update_file_expiry()` — 修改**

```python
# 原来:
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    ...
    conn.close()

# 改为:
    conn = get_conn()
    cursor = conn.cursor()
    ...
```

- [ ] **Step 12: `update_user_password()` — 修改**

```python
# 原来:
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    ...
    conn.close()

# 改为:
    conn = get_conn()
    cursor = conn.cursor()
    ...
```

- [ ] **Step 13: `update_downloads()` — 修改**

```python
# 原来:
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    ...
    conn.close()

# 改为:
    conn = get_conn()
    cursor = conn.cursor()
    ...
```

- [ ] **Step 14: `create_upload_session()` — 修改**

```python
# 原来:
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    ...
    conn.close()

# 改为:
    conn = get_conn()
    cursor = conn.cursor()
    ...
```

- [ ] **Step 15: `get_upload_session()` — 修改**

```python
# 原来:
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    ...
    conn.close()

# 改为:
    conn = get_conn()
    cursor = conn.cursor()
    ...
```

- [ ] **Step 16: `update_upload_session()` — 修改**

```python
# 原来:
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    ...
    conn.close()

# 改为:
    conn = get_conn()
    cursor = conn.cursor()
    ...
```

- [ ] **Step 17: `add_upload_chunk()` — 修改**

```python
# 原来:
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    ...
    conn.close()

# 改为:
    conn = get_conn()
    cursor = conn.cursor()
    ...
```

- [ ] **Step 18: `get_uploaded_chunks()` — 修改**

```python
# 原来:
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    ...
    conn.close()

# 改为:
    conn = get_conn()
    cursor = conn.cursor()
    ...
```

- [ ] **Step 19: `delete_upload_session()` — 修改**

```python
# 原来:
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    ...
    conn.close()

# 改为:
    conn = get_conn()
    cursor = conn.cursor()
    ...
```

- [ ] **Step 20: `cleanup_expired_sessions()` — 修改**

```python
# 原来:
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    ...
    conn.close()

# 改为:
    conn = get_conn()
    cursor = conn.cursor()
    ...
```

- [ ] **Step 21: 验证数据库模块导入和基本操作**

Run: `uv run python -c "
from services.database_service import init_db, get_user, get_conn
init_db()
conn = get_conn()
print('WAL mode:', conn.execute('PRAGMA journal_mode').fetchone()[0])
print('Row factory:', conn.row_factory)
"`
Expected: `WAL mode: wal` 且 `Row factory: <class 'sqlite3.Row'>`

- [ ] **Step 22: Commit**

```bash
git add services/database_service.py
git commit -m "refactor: use get_conn() for all database access functions"
```

---

### Task 3: 在 `init_db()` 中添加索引

**Files:**
- Modify: `services/database_service.py:31-114` (`init_db` 函数)

- [ ] **Step 1: 在 `init_db()` 中追加索引创建语句**

在 `init_db()` 函数的 `conn.commit()` 之前（第 113 行前），插入：

```python
    # 创建性能优化索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_username ON files(username)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_expiry_date ON files(expiry_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_file_hash ON files(file_hash)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_upload_sessions_session_id ON upload_sessions(session_id)")
```

- [ ] **Step 2: 验证索引创建**

Run: `uv run python -c "
from services.database_service import init_db
init_db()
import sqlite3
conn = sqlite3.connect('anyshare.db')
for row in conn.execute(\"SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'\"):
    print(row[0])
conn.close()
"`
Expected: 输出 4 个 `idx_` 开头的索引名。

- [ ] **Step 3: Commit**

```bash
git add services/database_service.py
git commit -m "feat: add database indexes for files and upload_sessions"
```

---

### Task 4: 静态资源 `Cache-Control` 头

**Files:**
- Modify: `web/routes.py:122-138` (`server_static` 函数)

- [ ] **Step 1: 在 `server_static` 中添加缓存头**

在 `server_static` 函数中，`app_logger.debug(...)` 之后、`return` 之前，插入：

```python
    # 根据文件类型设置缓存头
    _cache_ttl = {
        ".css": "public, max-age=86400",
        ".js": "public, max-age=86400",
        ".woff2": "public, max-age=604800",
        ".woff": "public, max-age=604800",
        ".ttf": "public, max-age=604800",
        ".png": "public, max-age=86400",
        ".jpg": "public, max-age=86400",
        ".jpeg": "public, max-age=86400",
        ".svg": "public, max-age=86400",
        ".ico": "public, max-age=86400",
    }
    _, suffix = os.path.splitext(filepath)
    cache_header = _cache_ttl.get(suffix.lower(), "no-cache")
    response.set_header("Cache-Control", cache_header)
```

- [ ] **Step 2: 验证缓存头**

Run: `uv run python -c "from web.routes import app; print('OK')"`
Expected: `OK`

然后启动服务器，用 curl 验证：
```bash
uv run python app.py &
sleep 2
curl -sI http://localhost:8000/static/css/style.css | grep -i cache-control
```
Expected: `Cache-Control: public, max-age=86400`

- [ ] **Step 3: 清理测试进程**

```bash
kill %1 2>/dev/null || true
```

- [ ] **Step 4: Commit**

```bash
git add web/routes.py
git commit -m "feat: add Cache-Control headers for static assets"
```

---

### Task 5: 端到端验证

- [ ] **Step 1: 启动服务器确认无异常**

```bash
uv run python app.py &
sleep 2
curl -s http://localhost:8000/api/healthz
```
Expected: `{"status": "ok"}`

- [ ] **Step 2: 验证首页加载**

```bash
curl -sI http://localhost:8000/ | head -1
```
Expected: `HTTP/1.1 200 OK`

- [ ] **Step 3: 清理并重启以验证 WAL 模式生效**

```bash
kill %1 2>/dev/null || true
sleep 1
ls -la anyshare.db-wal anyshare.db-shm 2>/dev/null || echo "WAL files will be created on first write"
```
Expected: 服务器运行后出现 `anyshare.db-wal` 和 `anyshare.db-shm` 文件。

- [ ] **Step 4: 验证索引可用**

```bash
sqlite3 anyshare.db "EXPLAIN QUERY PLAN SELECT * FROM files WHERE file_hash = 'test';"
```
Expected: 输出包含 `USING INDEX idx_files_file_hash`

- [ ] **Step 5: 清理测试进程**

```bash
kill %1 2>/dev/null || true
```

- [ ] **Step 6: Commit（如有文件变更）**

```bash
git status
```
