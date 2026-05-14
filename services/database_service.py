from datetime import UTC, datetime, timedelta
import os
import random
import sqlite3
import threading

from config import Config

config = Config()
DB_NAME = config.DB_NAME

_local = threading.local()


def get_conn() -> sqlite3.Connection:
    """返回当前线程复用的数据库连接，首次调用时启用 WAL 模式。"""
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
    return _local.conn


# 从环境变量读取管理员凭证
ADMIN_USERNAME = config.ADMIN_USERNAME
ADMIN_PASSWORD = config.ADMIN_PASSWORD


# 注册自定义适配器, 将 datetime 对象转换为字符串
def adapt_datetime(dt: datetime) -> str:
    return dt.isoformat()


# 注册自定义转换器, 将数据库中的字符串转换为 datetime 对象
def convert_datetime(s: bytes) -> datetime:
    return datetime.fromisoformat(s.decode("utf-8"))


# 注册适配器和转换器
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("datetime", convert_datetime)


def init_db() -> None:
    """
    初始化数据库。

    该函数负责创建并初始化数据库, 包括建立必要的表结构。
    它不接受任何参数, 也没有返回值。
    """
    # 连接到SQLite数据库, DB_NAME为数据库文件名
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()

    # 创建用户表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0,
        created_at DATETIME NOT NULL
    )
    """)

    # 创建文件表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_name TEXT NOT NULL,
        file_hash TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        upload_date DATETIME NOT NULL,
        expiry_date DATETIME NOT NULL,
        password TEXT NOT NULL,
        upload_ip TEXT NOT NULL,
        downloads INTEGER DEFAULT 0,
        username TEXT NOT NULL
    )
    """)

    # 创建上传会话表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS upload_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT UNIQUE NOT NULL,
        file_name TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        chunk_size INTEGER NOT NULL,
        total_chunks INTEGER NOT NULL,
        uploaded_chunks TEXT DEFAULT '',
        file_hash TEXT,
        username TEXT DEFAULT 'anonymous',
        upload_ip TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'uploading'
    )
    """)

    # 创建分片表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS upload_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        chunk_hash TEXT NOT NULL,
        chunk_size INTEGER NOT NULL,
        uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(session_id, chunk_index)
    )
    """)

    # 检查是否已存在管理员账户
    cursor.execute("SELECT * FROM users WHERE is_admin = 1")

    # 如果不存在管理员账户, 创建默认管理员
    if not cursor.fetchone():
        # 创建默认管理员账户
        cursor.execute(
            "INSERT INTO users (username, password, is_admin, created_at) VALUES (?, ?, ?, ?)",
            (ADMIN_USERNAME, ADMIN_PASSWORD, 1, datetime.now(tz=UTC)),
        )

    # 提交事务并关闭数据库连接
    conn.commit()
    conn.close()


def add_file(
    file_name: str,
    file_hash: str,
    file_size: int,
    expiry_date: datetime,
    upload_ip: str,
    username: str,
    password: str | None = None,
) -> str:
    """
    将文件信息添加到数据库中。

    生成文件哈希和密码, 然后将文件信息插入到数据库中。

    参数:
    filename (str): 文件名。
    file_size (int): 文件大小, 以字节为单位。
    expiry_date (datetime): 文件过期日期。
    upload_ip (str): 文件上传者的IP地址。
    username (str): 上传用户名。
    password (str, optional): 文件密码。如果未提供, 将生成一个随机密码。

    返回:
    tuple: 文件密码。
    """
    # 连接到SQLite数据库, DB_NAME为数据库文件的路径
    conn = get_conn()
    cursor = conn.cursor()

    # 获取当前的UTC时间作为上传日期
    upload_date = datetime.now(tz=UTC)

    # 如果没有提供密码, 生成随机6位密码
    if password is None:
        password = "".join(random.choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=6))

    # 将文件信息插入到数据库中
    cursor.execute(
        "INSERT INTO files (file_name, file_hash, file_size, upload_date, expiry_date, password, upload_ip, username) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            file_name,
            file_hash,
            file_size,
            upload_date,
            expiry_date,
            password,
            upload_ip,
            username,
        ),
    )

    # 提交数据库事务
    conn.commit()

    # 返回文件密码
    return password


def get_user_files(username: str) -> list:
    """
    获取指定用户上传的所有文件

    参数:
    username (str): 用户名

    返回:
    list: 包含用户文件信息的字典列表
    """
    conn = get_conn()
    cursor = conn.cursor()

    # 检查用户是否为管理员
    user_info = get_user(username)
    if user_info and user_info["is_admin"] == 1:
        # 管理员可以看到所有文件
        cursor.execute("SELECT * FROM files ORDER BY upload_date DESC")
    else:
        # 普通用户只能看到自己的文件
        cursor.execute("SELECT * FROM files WHERE username = ? ORDER BY upload_date DESC", (username,))

    files = cursor.fetchall()

    # 将文件信息转换为字典列表, 并处理datetime对象
    files_list = []
    for file in [dict(file) for file in files]:
        # 将datetime对象转换为ISO格式字符串
        if file.get("upload_date"):
            file["upload_date"] = file["upload_date"].isoformat()
        if file.get("expiry_date"):
            file["expiry_date"] = file["expiry_date"].isoformat()
        files_list.append(file)

    return files_list


def get_file(file_hash: str) -> dict | None:
    """
    根据文件哈希值获取文件信息。

    参数:
    file_hash (str): 文件的哈希值。

    返回:
    dict: 包含文件信息的字典, 如果找不到则返回None。
    """
    # 连接到SQLite数据库, 检测类型
    conn = get_conn()
    cursor = conn.cursor()

    # 执行查询语句, 查找匹配的文件哈希值
    cursor.execute("SELECT * FROM files WHERE file_hash = ?", (file_hash,))
    file = cursor.fetchone()

    # 如果找到了匹配的文件
    if file:
        # 转换为字典
        file_dict = dict(file)

        # 将datetime对象转换为ISO格式字符串
        if file_dict.get("upload_date"):
            file_dict["upload_date"] = file_dict["upload_date"].isoformat()
        if file_dict.get("expiry_date"):
            file_dict["expiry_date"] = file_dict["expiry_date"].isoformat()

        # 格式化文件大小
        size_mib = file_dict["file_size"] / (1024 * 1024)
        file_dict["size_formatted"] = f"{size_mib:.2f} MiB"

        # 返回文件信息字典
        return file_dict

    # 如果没有找到匹配的文件, 返回None
    return None


def delete_expired_files() -> None:
    """
    删除过期文件(过期超过30天)
    """
    conn = get_conn()
    cursor = conn.cursor()

    # 计算30天前的时间
    threshold_date = datetime.now(tz=UTC) - timedelta(days=30)

    # 查询过期超过30天的文件
    cursor.execute("SELECT file_hash FROM files WHERE expiry_date < ?", (threshold_date,))
    expired_files = cursor.fetchall()

    # 删除文件记录和物理文件
    for file_record in expired_files:
        file_hash = file_record[0]
        file_path = os.path.join("./upload", file_hash)

        # 删除物理文件
        if os.path.exists(file_path):
            os.remove(file_path)

        # 删除数据库记录
        cursor.execute("DELETE FROM files WHERE file_hash = ?", (file_hash,))

    conn.commit()

    # 记录日志
    if len(expired_files) > 0:
        print(f"Cleaned up {len(expired_files)} expired files")


def delete_file_from_db(file_hash: str) -> None:
    """
    从数据库中删除指定文件记录。

    连接数据库, 执行删除操作, 移除files表中与给定文件哈希值匹配的行。

    参数:
    file_hash (str): 文件的哈希值, 用于唯一标识并定位数据库中的文件记录。

    返回:
    无
    """
    conn = get_conn()
    cursor = conn.cursor()

    # 执行删除操作, 使用参数化查询以防止SQL注入
    cursor.execute("DELETE FROM files WHERE file_hash = ?", (file_hash,))

    # 提交更改
    conn.commit()


def add_user(username: str, password: str, is_admin: int = 0) -> bool | None:
    """
    添加新用户到数据库

    参数:
    username (str): 用户名
    password (str): 密码
    is_admin (int): 是否为管理员, 1表示是, 0表示否

    返回:
    bool: 添加成功返回True, 失败返回False
    """
    try:
        conn = get_conn()
        cursor = conn.cursor()

        # 检查用户名是否已存在
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return False

        # 添加新用户
        cursor.execute(
            "INSERT INTO users (username, password, is_admin, created_at) VALUES (?, ?, ?, ?)",
            (username, password, is_admin, datetime.now(tz=UTC)),
        )

        conn.commit()
        return True
    except Exception:
        return False


def get_user(username: str, password: str | None = None) -> dict | None:
    """
    根据用户名和可选的密码获取用户信息

    参数:
    username (str): 用户名
    password (str, optional): 密码, 如果提供则验证密码

    返回:
    dict: 用户信息字典, 如果用户不存在或密码错误则返回None
    """
    conn = get_conn()
    cursor = conn.cursor()

    if password:
        cursor.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password),
        )
    else:
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))

    user = cursor.fetchone()

    if user:
        return dict(user)
    return None


def get_all_users() -> list:
    """
    获取所有用户信息

    返回:
    list: 包含所有用户信息的字典列表
    """
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users ORDER BY id")
    users = cursor.fetchall()

    # 将用户信息转换为字典列表, 并处理datetime对象
    users_list = []
    for user in [dict(user) for user in users]:
        # 将datetime对象转换为ISO格式字符串
        if user.get("created_at"):
            user["created_at"] = user["created_at"].isoformat()
        users_list.append(user)

    return users_list


def delete_user(username: str) -> bool | None:
    """
    删除指定用户

    参数:
    username (str): 用户名

    返回:
    bool: 删除成功返回True, 失败返回False
    """
    try:
        conn = get_conn()
        cursor = conn.cursor()

        # 检查是否是管理员账户
        cursor.execute("SELECT is_admin FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()

        # 如果是管理员账户, 不允许删除
        if result and result[0] == 1:
            return False

        # 删除用户
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))

        conn.commit()
        return True
    except Exception as e:
        print(f"删除用户失败: {str(e)}")
        return False


def update_file_expiry(file_hash: str, new_expiry_date: datetime) -> bool | None:
    """
    更新文件的过期时间

    参数:
    file_hash (str): 文件哈希
    new_expiry_date (datetime): 新的过期时间

    返回:
    bool: 更新成功返回True, 失败返回False
    """
    try:
        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE files SET expiry_date = ? WHERE file_hash = ?",
            (new_expiry_date, file_hash),
        )

        conn.commit()
        return True
    except Exception as e:
        print(f"更新文件过期时间失败: {str(e)}")
        return False


def update_user_password(username: str, new_password: str) -> bool | None:
    """
    更新用户密码

    参数:
    username (str): 用户名
    new_password (str): 新密码

    返回:
    bool: 更新成功返回True, 失败返回False
    """
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password = ? WHERE username = ?",
            (new_password, username),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"更新用户密码失败: {str(e)}")
        return False


def update_downloads(file_hash: str) -> bool | None:
    """
    更新文件的下载次数
    参数:
    file_hash (str): 文件哈希
    返回:
    bool: 更新成功返回True, 失败返回False
    """
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE files SET downloads = downloads + 1 WHERE file_hash =?",
            (file_hash,),
        )
        conn.commit()
        return True
    except Exception:
        return False


# 分片上传相关函数
def create_upload_session(
    session_id: str,
    file_name: str,
    file_size: int,
    chunk_size: int,
    total_chunks: int,
    username: str,
    upload_ip: str,
) -> bool | None:
    """
    创建上传会话

    参数:
    session_id (str): 会话ID
    file_name (str): 文件名
    file_size (int): 文件大小
    chunk_size (int): 分片大小
    total_chunks (int): 总分片数
    username (str): 用户名
    upload_ip (str): 上传IP

    返回:
    bool: 创建成功返回True, 失败返回False
    """
    try:
        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO upload_sessions
            (session_id, file_name, file_size, chunk_size, total_chunks, username, upload_ip, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                session_id,
                file_name,
                file_size,
                chunk_size,
                total_chunks,
                username,
                upload_ip,
                datetime.now(tz=UTC),
                datetime.now(tz=UTC),
            ),
        )

        conn.commit()
        return True
    except Exception:
        return False


def get_upload_session(session_id: str) -> dict | None:
    """
    获取上传会话信息

    参数:
    session_id (str): 会话ID

    返回:
    dict: 会话信息字典, 如果不存在则返回None
    """
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM upload_sessions WHERE session_id = ?", (session_id,))
    session = cursor.fetchone()

    if session:
        session_dict = dict(session)
        # 处理datetime对象
        if session_dict.get("created_at"):
            session_dict["created_at"] = session_dict["created_at"].isoformat()
        if session_dict.get("updated_at"):
            session_dict["updated_at"] = session_dict["updated_at"].isoformat()
        return session_dict
    return None


def update_upload_session(
    session_id: str,
    uploaded_chunks: str | None = None,
    file_hash: str | None = None,
    status: str | None = None,
) -> bool | None:
    """
    更新上传会话

    参数:
    session_id (str): 会话ID
    uploaded_chunks (str): 已上传分片列表
    file_hash (str): 文件哈希
    status (str): 状态

    返回:
    bool: 更新成功返回True, 失败返回False
    """
    try:
        conn = get_conn()
        cursor = conn.cursor()

        update_fields = ["updated_at = ?"]
        params = [datetime.now(tz=UTC)]

        if uploaded_chunks is not None:
            update_fields.append("uploaded_chunks = ?")
            params.append(uploaded_chunks)

        if file_hash is not None:
            update_fields.append("file_hash = ?")
            params.append(file_hash)

        if status is not None:
            update_fields.append("status = ?")
            params.append(status)

        params.append(session_id)

        cursor.execute(f"UPDATE upload_sessions SET {', '.join(update_fields)} WHERE session_id = ?", params)

        conn.commit()
        return True
    except Exception:
        return False


def add_upload_chunk(
    session_id: str,
    chunk_index: int,
    chunk_hash: str,
    chunk_size: int,
) -> bool | None:
    """
    添加上传分片记录

    参数:
    session_id (str): 会话ID
    chunk_index (int): 分片索引
    chunk_hash (str): 分片哈希
    chunk_size (int): 分片大小

    返回:
    bool: 添加成功返回True, 失败返回False
    """
    try:
        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO upload_chunks
            (session_id, chunk_index, chunk_hash, chunk_size, uploaded_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (session_id, chunk_index, chunk_hash, chunk_size, datetime.now(tz=UTC)),
        )

        conn.commit()
        return True
    except Exception:
        return False


def get_uploaded_chunks(session_id: str) -> list:
    """
    获取已上传的分片列表

    参数:
    session_id (str): 会话ID

    返回:
    list: 已上传分片索引列表
    """
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT chunk_index FROM upload_chunks WHERE session_id = ? ORDER BY chunk_index", (session_id,))
    chunks = cursor.fetchall()

    return [chunk[0] for chunk in chunks]


def delete_upload_session(session_id: str) -> bool | None:
    """
    删除上传会话及相关分片记录

    参数:
    session_id (str): 会话ID

    返回:
    bool: 删除成功返回True, 失败返回False
    """
    try:
        conn = get_conn()
        cursor = conn.cursor()

        # 删除分片记录
        cursor.execute("DELETE FROM upload_chunks WHERE session_id = ?", (session_id,))
        # 删除会话记录
        cursor.execute("DELETE FROM upload_sessions WHERE session_id = ?", (session_id,))

        conn.commit()
        return True
    except Exception:
        return False


def cleanup_expired_sessions() -> bool | None:
    """
    清理过期的上传会话(超过24小时)
    """
    try:
        conn = get_conn()
        cursor = conn.cursor()

        # 计算24小时前的时间
        threshold_date = datetime.now(tz=UTC) - timedelta(hours=24)

        # 查询过期会话
        cursor.execute(
            "SELECT session_id FROM upload_sessions WHERE created_at < ? AND status != 'completed'", (threshold_date,)
        )
        expired_sessions = cursor.fetchall()

        # 删除过期会话及相关分片
        for session in expired_sessions:
            session_id = session[0]
            cursor.execute("DELETE FROM upload_chunks WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM upload_sessions WHERE session_id = ?", (session_id,))

            # 删除临时分片文件
            import os

            temp_dir = f"./upload/temp/{session_id}"
            if os.path.exists(temp_dir):
                import shutil

                shutil.rmtree(temp_dir)

        conn.commit()

        if len(expired_sessions) > 0:
            print(f"Cleaned up {len(expired_sessions)} expired upload sessions")

        return True
    except Exception as e:
        print(f"Failed to cleanup expired sessions: {str(e)}")
        return False
