# AnyShare 性能优化 — 方案 A：低成本快速优化

## 背景

AnyShare 基于 Bottle + Waitress + SQLite，服务于 10-50 人团队。代码审查发现数据库连接管理、WAL 模式缺失、索引缺失、静态资源无缓存、日志级别过高等问题。

## 目标

- 页面响应速度提升 30-50%
- 并发读写能力提升 2-3 倍
- 改动量 < 60 行，3 个文件
- 不改架构，零风险

## 变更清单

### 1. 数据库连接复用 + WAL 模式

**文件：`services/database_service.py`**

- 新增 `threading.local()` 存储线程本地连接
- 新增 `get_conn()` 函数，返回当前线程复用的连接，首次调用时建立连接并设置 WAL 模式
- 所有数据访问函数（`add_file`、`get_file`、`get_user_files`、`delete_file_from_db`、`delete_expired_files`、`add_user`、`get_user`、`get_all_users`、`delete_user`、`update_file_expiry`、`update_user_password`、`update_downloads`、`create_upload_session`、`get_upload_session`、`update_upload_session`、`add_upload_chunk`、`get_uploaded_chunks`、`delete_upload_session`、`cleanup_expired_sessions`）不再各自调用 `sqlite3.connect()` / `conn.close()`，改为调用 `get_conn()`
- `init_db()` 保留独立连接（启动时调用，不在请求线程内）

WAL 模式关键 SQL：
```sql
PRAGMA journal_mode=WAL;
```

### 2. 添加数据库索引

**文件：`services/database_service.py` `init_db()`**

```sql
CREATE INDEX IF NOT EXISTS idx_files_username ON files(username);
CREATE INDEX IF NOT EXISTS idx_files_expiry_date ON files(expiry_date);
CREATE INDEX IF NOT EXISTS idx_files_file_hash ON files(file_hash);
CREATE INDEX IF NOT EXISTS idx_upload_sessions_session_id ON upload_sessions(session_id);
```

- `file_hash`：最频繁的查询条件（下载、删除、过期更新）
- `username`：管理页面和用户文件页面
- `expiry_date`：过期文件清理定时任务
- `session_id`：分片上传会话查询

### 3. 静态资源 Cache-Control

**文件：`web/routes.py` `server_static()`**

根据文件后缀设置 `Cache-Control` 响应头：

| 类型 | 缓存时间 |
|------|----------|
| `.css` | `public, max-age=86400` (1 天) |
| `.js` | `public, max-age=86400` (1 天) |
| `.woff2` | `public, max-age=604800` (7 天) |
| `.png` / `.jpg` / `.svg` | `public, max-age=86400` (1 天) |
| 其他 | `no-cache` (保持默认) |

### 4. 日志级别

不修改代码。通过环境变量 `LOG_LEVEL=INFO` 控制生产环境日志级别，减少同步磁盘 I/O。

## 不改的内容

- 不引入连接池库（SQLite 文件级锁，连接池无意义）
- 不修改 Waitress 线程配置（单独调优，不在本次范围）
- 不改变任何业务逻辑和 API

## 验证方式

1. `uv run python app.py` 启动，确认无报错
2. 上传文件 → 下载文件 → 验证文件过期清理，确认功能正常
3. 浏览器 DevTools Network 面板确认静态资源返回 `Cache-Control` 头且状态 `200 (from disk cache)`
4. 查看日志文件确认日志量减少（INFO vs DEBUG）

## 回滚

所有改动完全可逆：
- 数据库索引可用 `DROP INDEX` 回滚
- WAL 模式可通过 `PRAGMA journal_mode=DELETE` 回滚
- 连接复用和缓存头纯代码变更，git revert 即可
