import hashlib
import random
import sqlite3
from datetime import datetime, timezone

DB_NAME = "anyshare.db"


# 注册自定义适配器，将 datetime 对象转换为字符串
def adapt_datetime(dt):
    return dt.isoformat()


# 注册自定义转换器，将数据库中的字符串转换为 datetime 对象
def convert_datetime(s):
    return datetime.fromisoformat(s.decode("utf-8"))


# 注册适配器和转换器
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("datetime", convert_datetime)


def init_db():
    """
    初始化数据库。

    该函数负责创建并初始化数据库，包括建立必要的表结构。
    它不接受任何参数，也没有返回值。
    """
    # 连接到SQLite数据库，DB_NAME为数据库文件名
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()

    # 创建文件表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id TEXT NOT NULL,
        filename TEXT NOT NULL,
        file_hash TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        upload_date DATETIME NOT NULL,
        expiry_date DATETIME NOT NULL,
        password TEXT NOT NULL,
        upload_ip TEXT NOT NULL
    )
    """)

    # 提交事务并关闭数据库连接
    conn.commit()
    conn.close()


def add_file(filename, file_id, file_size, expiry_date, upload_ip):
    """
    将文件信息添加到数据库中。

    生成文件哈希和密码，然后将文件信息插入到数据库中。

    参数:
    filename (str): 文件名。
    file_id (int): 文件ID。
    file_size (int): 文件大小，以字节为单位。
    expiry_date (datetime): 文件过期日期。
    upload_ip (str): 文件上传者的IP地址。

    返回:
    tuple: 包含文件哈希和密码的元组。
    """
    # 连接到SQLite数据库，DB_NAME为数据库文件的路径
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()

    # 获取当前的UTC时间作为上传日期
    upload_date = datetime.now(tz=timezone.utc)

    # 生成文件哈希
    hash_input = f"{file_id}_{filename}_{upload_date.timestamp()}"
    file_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    # 生成随机6位密码
    password = "".join(random.choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=6))

    # 将文件信息插入到数据库中
    cursor.execute(
        "INSERT INTO files (file_id, filename, file_hash, file_size, upload_date, expiry_date, password, upload_ip) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (file_id, filename, file_hash, file_size, upload_date, expiry_date, password, upload_ip),
    )

    # 提交数据库事务
    conn.commit()
    # 关闭数据库连接
    conn.close()

    # 返回文件哈希和密码
    return file_hash, password


def get_file(file_hash):
    """
    根据文件哈希值获取文件信息。

    参数:
    file_hash (str): 文件的哈希值。

    返回:
    dict: 包含文件信息的字典，如果找不到则返回None。
    """
    # 连接到SQLite数据库，检测类型
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 执行查询语句，查找匹配的文件哈希值
    cursor.execute("SELECT * FROM files WHERE file_hash = ?", (file_hash,))
    file = cursor.fetchone()

    # 关闭数据库连接
    conn.close()

    # 如果找到了匹配的文件
    if file:
        # 转换为字典
        file_dict = dict(file)

        # 格式化文件大小
        size_mib = file_dict["file_size"] / (1024 * 1024)
        file_dict["size_formatted"] = f"{size_mib:.2f} MiB"

        # 返回文件信息字典
        return file_dict

    # 如果没有找到匹配的文件，返回None
    return None


def get_all_files():
    """
    从数据库中获取所有文件信息。

    此函数连接到SQLite数据库, 查询files表中的所有记录, 并将结果以字典列表的形式返回。
    没有输入参数。
    返回值：包含所有文件信息的字典列表。
    """
    # 连接到SQLite数据库，DB_NAME为数据库名
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    # 设置行工厂以获取行数据
    conn.row_factory = sqlite3.Row
    # 创建游标对象以执行SQL命令
    cursor = conn.cursor()

    # 执行SQL查询，选择files表中的所有记录
    cursor.execute("SELECT * FROM files")
    # 获取所有查询结果
    files = cursor.fetchall()

    # 关闭数据库连接
    conn.close()

    # 将查询结果转换为字典列表并返回
    return [dict(file) for file in files]


def delete_expired_files():
    """
    删除过期文件

    本函数连接到数据库，获取当前时间，并删除所有过期的文件
    过期文件是指那些在当前时间之前的文件
    """
    # 连接到数据库，启用类型检测以解析声明类型
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()

    # 获取当前的UTC时间，用于比较文件的过期时间
    now = datetime.now(tz=timezone.utc)
    
    # 执行SQL语句，删除所有过期的文件
    cursor.execute("DELETE FROM files WHERE expiry_date < ?", (now,))

    # 提交事务，确保对数据库的更改被保存
    conn.commit()
    
    # 关闭数据库连接，释放资源
    conn.close()


def delete_file_from_db(file_hash):
    """
    从数据库中删除指定文件记录。

    连接数据库，执行删除操作，移除files表中与给定文件哈希值匹配的行。

    参数:
    file_hash (str): 文件的哈希值，用于唯一标识并定位数据库中的文件记录。

    返回:
    无
    """
    # 连接数据库，确保类型检测
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()

    # 执行删除操作，使用参数化查询以防止SQL注入
    cursor.execute("DELETE FROM files WHERE file_hash = ?", (file_hash,))

    # 提交更改并关闭数据库连接
    conn.commit()
    conn.close()
