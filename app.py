import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from logging.handlers import TimedRotatingFileHandler

from bottle import Bottle, redirect, request, response, static_file, template
from waitress import serve

from database import add_file, delete_file_from_db, get_all_files, get_file, init_db

# 创建Bottle应用
app = Bottle()


# 配置
UPLOAD_FOLDER = "./upload"
LOG_FOLDER = "./log"

# 从环境变量读取管理员凭证
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
ANONYMOUS = os.getenv("ANONYMOUS", "true")
FILE_LIMIT_SIZE = os.getenv("FILE_LIMIT_SIZE", "10.00")

# 创建上传文件夹和日志文件夹
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)

# 初始化数据库
init_db()


# 静态文件路由
@app.route("/static/<filepath:path>")
def server_static(filepath):
    """
    提供静态文件下载服务

    本路由用于访问项目中的静态资源, 如CSS、JavaScript文件和图片等
    它允许Web客户端通过URL请求特定的静态文件

    参数:
    - filepath: 要访问的静态文件路径，是一个动态参数，可以匹配多层路径

    返回:
    - static_file对象, 根据给定的文件路径和根目录返回相应的静态文件
    """
    app_logger.debug(f"Static file requested: {filepath}")
    return static_file(filepath, root="./static")


# 主页路由装饰器，将根路径 "/" 关联到 index 函数
@app.route("/")
def index():
    """
    主页处理函数。

    检查用户是否已经以匿名方式登录, 如果已匿名登录或通过cookie验证, 则渲染主页模板。
    否则，重定向到登录页面。
    """
    # 检查是否已登录或者匿名登陆
    if ANONYMOUS == "true" or request.get_cookie("anyShare", secret="<5}>h~1RU4EXP87") == "true":
        app_logger.info(f"Index page accessed, user is anonymous or logged in, Client-IP: {request.headers.get('x-forwarded-for', request.remote_addr)}")
        # 渲染主页模板并传递文件大小限制参数
        return template("views/index.html", file_limit_size=FILE_LIMIT_SIZE)
    else:
        app_logger.info("Index page accessed, user not logged in, redirect to login.")
        # 重定向到登录页面
        return redirect("/login")


# 处理文件上传, 并在服务端验证文件大小限制(防止用户前端修改css脚本实现文件大小限制解除), 并返回文件信息
@app.route("/upload", method="POST")
def upload():
    """
    处理文件上传请求。

    此函数首先检查用户是否已登录或匿名登录。如果未满足登录条件，则返回未经授权的错误。
    接着，函数会检查上传的文件是否存在，计算文件大小，并验证是否超过允许的最大大小。
    如果文件过大，将删除文件并返回错误信息。
    最后，函数会根据用户选择的过期时间选项，计算文件的过期日期，并将文件信息保存到数据库。

    Returns:
        dict: 包含上传状态、文件ID、文件哈希、文件名、大小、过期选项、密码和上传IP的信息。
    """
    # 检查是否已登录或者匿名登陆
    if ANONYMOUS != "true" and request.get_cookie("anyShare", secret="<5}>h~1RU4EXP87") != "true":
        app_logger.warning(f"Unauthorized upload attempt from IP: {request.headers.get('x-forwarded-for', request.remote_addr)}")
        return {"status": "error", "message": "unauthorized"}

    upload_file = request.files.get("file")
    if not upload_file:
        app_logger.warning("Upload request received without file selection")
        return {"status": "error", "message": "no file is selected"}

    try:
        total_size = 0
        max_size_bytes = float(FILE_LIMIT_SIZE) * 1024 * 1024
        # 获取文件信息
        file_name = request.forms.get("file_name")
        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        # 构建文件保存路径
        file_path = os.path.join(UPLOAD_FOLDER, file_id)
        # 获取客户端IP(支持反向代理)
        upload_ip = request.headers.get("x-forwarded-for", request.remote_addr)
        # 处理多个代理IP的情况
        if "," in upload_ip:
            upload_ip = upload_ip.split(",")[0].strip()

        # 流式读取文件并计算总大小, 每次读取8KB
        app_logger.info(f"File upload started: '{file_name}', Client-IP: {upload_ip}")

        with open(file_path, "wb") as f:
            while chunk := upload_file.file.read(8192):
                f.write(chunk)
                total_size += len(chunk)
                if total_size > max_size_bytes:
                    app_logger.warning(f"File size exceeded limit: '{file_name}', Client-IP: {upload_ip}")
                    os.remove(file_path)
                    return {"status": "error", "message": f"File size over the limit of {FILE_LIMIT_SIZE} MiB"}

        # 获取过期时间
        expiry_option = request.forms.get("expiry", "1 day")
        expiry_map = {
            "1 hour": datetime.now(tz=timezone.utc) + timedelta(hours=1),
            "1 day": datetime.now(tz=timezone.utc) + timedelta(days=1),
            "1 week": datetime.now(tz=timezone.utc) + timedelta(weeks=1),
            "1 month": datetime.now(tz=timezone.utc) + timedelta(days=30),
            "forever": datetime.now(tz=timezone.utc) + timedelta(days=365 * 10),
        }
        expiry_date = expiry_map.get(expiry_option, datetime.now(tz=timezone.utc) + timedelta(days=1))

        # 保存到数据库
        file_hash, password = add_file(file_name, file_id, total_size, expiry_date, upload_ip)

        app_logger.info(f"File upload completed: '{file_name}', hash: {file_hash}, expiry: {expiry_option}, size: {total_size} bytes, Client-IP: {upload_ip}")
        return {"status": "success", "file_id": file_id, "file_hash": file_hash, "file_name": file_name, "size": total_size, "expiry": expiry_option, "password": password, "upload_ip": upload_ip}
    except Exception as e:
        app_logger.error(f"File upload failed: '{file_name if 'file_name' in locals() else 'unknown'}', error: {str(e)}")
        if "file_path" in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
                app_logger.warning(f"Partial file removed due to error: {file_path}")
            except Exception as remove_err:
                app_logger.error(f"Failed to remove partial file: {file_path}, error: {str(remove_err)}")
        return {"status": "error", "message": f"An error occurred: {str(e)}"}


# 处理文件上传成功后的页面逻辑
@app.route("/upload", method="GET")
def upload_success():
    """
    检查用户登录状态，如果未登录或未匿名登录，则重定向到登录页面。
    如果提供了文件信息，则解析文件信息并渲染上传成功的页面；否则重定向到主页。
    """
    # 检查是否已登录或者匿名登陆
    if ANONYMOUS != "true" and request.get_cookie("anyShare", secret="<5}>h~1RU4EXP87") != "true":
        # 如果未登录且非匿名登录，重定向到登录页面
        return redirect("/login")

    # 获取URL参数中的文件信息字符串
    file_info_str = request.query.get("file_info")
    # 如果没有文件信息，则重定向到主页
    if not file_info_str:
        return redirect("/")

    try:
        # 解析URL参数中的JSON字符串
        import json

        file_info = json.loads(file_info_str)

        # 直接使用解析后的文件信息渲染模板
        return template("views/upload.html", file_info=file_info)
    except Exception as e:
        # 如果解析文件信息时发生错误，渲染错误页面
        return template("error.html", error=f"Error parsing file information: {str(e)}")


# 获取文件信息
@app.route("/file")
def get_file_info():
    """
    根据文件哈希和密码获取文件信息。
    从请求查询中获取文件哈希和密码，验证文件是否存在和有效，以及密码是否正确。
    如果文件不存在或已过期，显示错误信息。如果密码正确，提供文件下载。
    如果未提供密码或密码错误，提示用户输入正确的密码。
    """
    # 从查询参数中获取文件哈希和密码
    file_hash = request.query.get("hash")
    password = request.query.get("pwd")

    # 如果没有文件哈希，则重定向到主页
    if not file_hash:
        app_logger.warning("File info requested without hash, redirect to index.")
        redirect("/")

    # 根据文件哈希获取文件信息
    file_info = get_file(file_hash)

    # 如果文件信息不存在，显示错误信息
    if not file_info:
        app_logger.warning(f"Attempt to access non-existent or expired file: {file_hash}, Client-IP: {request.headers.get('x-forwarded-for', request.remote_addr)}")
        return template("views/error.html", message="The file does not exist or has expired")

    # 检查是否过期
    expiry_date = file_info["expiry_date"]
    if expiry_date < datetime.now(tz=timezone.utc):
        app_logger.info(f"Attempt to access expired file: {file_hash}, expired on: {expiry_date}, Client-IP: {request.headers.get('x-forwarded-for', request.remote_addr)}")
        return template("views/error.html", message="Sharing has expired")

    # 如果提供了密码，检查密码是否正确
    if password:
        if password == file_info["password"]:
            app_logger.info(f"File download started: '{file_info['file_name']}', hash: {file_hash}, Client-IP: {request.headers.get('x-forwarded-for', request.remote_addr)}")
            return static_file(file_info["file_id"], root=UPLOAD_FOLDER, download=file_info["file_name"])
        else:
            app_logger.warning(f"Incorrect password provided for file: {file_hash}, Client-IP: {request.headers.get('x-forwarded-for', request.remote_addr)}")
            return template("views/password.html", file_hash=file_hash, error="password error")

    app_logger.info(f"Password required for file: {file_hash}, Client-IP: {request.headers.get('x-forwarded-for', request.remote_addr)}")
    return template("views/password.html", file_hash=file_hash, error=None)


# 处理密码提交
@app.route("/verify", method="POST")
def verify_password():
    """
    验证密码并重定向到对应的文件下载页面。

    该函数通过POST请求获取用户提交的文件哈希值和密码, 然后检查这些信息是否完整。
    如果任一信息缺失，将返回错误页面。否则，将用户重定向到带有密码的文件链接。
    """
    # 获取用户提交的文件哈希值和密码
    file_hash = request.forms.get("hash")
    password = request.forms.get("password")

    # 检查文件哈希值和密码是否都已提供
    if not file_hash or not password:
        # 返回错误页面，提示参数错误
        return template("views/error.html", message="parameter error")

    # 重定向到带密码的文件链接
    return redirect(f"/file?hash={file_hash}&pwd={password}")


# 下载文件,该路由不需要pwd支持通过文件hash下载
# @app.route("/download/<file_hash>")
# def download_file(file_hash):
#     file_info = get_file(file_hash)
#     if not file_info:
#         return template("views/error.html", message="The file does not exist or has expired")

#     return static_file(file_info["file_id"], root=UPLOAD_FOLDER, download=file_info["file_name"])


# 删除过期文件的任务（实际应用中应使用定时任务）
def cleanup_expired_files():
    """
    本函数用于定期清理过期文件。
    由于文件过期判定逻辑较为复杂，涉及文件最后修改时间与当前时间的比较，
    以及过期时间阈值的设定，建议在实际应用中使用定时任务来调用本函数，
    以减少手动触发清理任务的需求。

    无参数。

    无返回值。
    """
    # 实现删除过期文件的逻辑
    pass


# 管理员登录页面
@app.route("/login")
def login_page():
    """
    渲染并返回登录页面。

    该函数通过装饰器@app.route("/login")与URL路径/login关联
    当访问该路径时, Flask框架将调用此函数。

    参数:
    无

    返回:
    返回渲染后的登录页面HTML, 错误信息为None, 表示初次加载登录页时没有错误信息。
    """
    return template("views/login.html", error=None)


# 处理管理员登录
@app.route("/login", method="POST")
def login():
    """
    管理员登录验证函数。

    该函数首先从请求中获取用户名和密码，然后与预定义的管理员用户名和密码进行比较。
    如果验证成功, 设置会话cookie并重定向到管理员页面; 否则返回登录页面并显示错误信息。
    """
    # 获取登录表单中的用户名和密码
    username = request.forms.get("username")
    password = request.forms.get("password")

    # 简单的管理员验证（实际应用中应使用更安全的方式）
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        # 设置会话cookie
        response.set_cookie("anyShare", "true", secret="<5}>h~1RU4EXP87", path="/")
        # 验证成功，重定向到管理员页面
        return redirect("/admin")
    else:
        app_logger.warning(f"Failed admin login attempt with username: {username}, Client-IP: {request.headers.get('x-forwarded-for', request.remote_addr)}")
        return template("views/login.html", error="username or password is error")


# 管理员页面
@app.route("/admin")
def admin_page():
    """
    管理员页面路由。
    检查用户是否已登录，如果未登录则重定向到登录页面。
    获取所有文件的列表，计算并格式化相关统计信息，然后渲染管理员页面模板。
    """

    # 检查是否已登录
    if request.get_cookie("anyShare", secret="<5}>h~1RU4EXP87") != "true":
        app_logger.info(f"Unauthorized admin page access attempt, redirect to login, Client-IP: {request.headers.get('x-forwarded-for', request.remote_addr)}")
        return redirect("/login")

    # 获取所有文件
    files = get_all_files()
    app_logger.info(f"Admin page accessed, total files: {len(files)}")

    # 计算统计信息
    active_files = len(files)
    total_size = sum(file["file_size"] for file in files)

    # 格式化存储大小
    storage_used = format_size(total_size)
    storage_limit = "2.00 GiB"  # 可以从配置中读取

    # 格式化时间和存储空间
    for file in files:
        # 上传时间
        upload_date = file["upload_date"]
        file["upload_formatted"] = upload_date.strftime("%Y-%m-%d %H:%M:%S")
        file["upload_relative"] = get_relative_time(upload_date)

        # 过期时间
        expiry_date = file["expiry_date"]
        file["expiry_formatted"] = expiry_date.strftime("%Y-%m-%d %H:%M:%S")
        file["expiry_relative"] = get_relative_time(expiry_date)

        # 格式化存储空间
        file["size_formatted"] = format_size(file["file_size"])

    # 编译统计信息字典
    stats = {"active_files": active_files, "storage_used": storage_used, "storage_limit": storage_limit}

    # 渲染管理员页面模板
    return template("views/admin.html", files=files, stats=stats)


# 获取管理统计数据
@app.route("/admin/stats")
def get_admin_stats():
    """
    获取管理员统计信息的路由处理函数。
    检查用户是否已登录，然后计算和返回文件统计信息。

    Returns:
        dict: 包含统计信息的字典，如活跃文件数和存储使用情况。
    """
    # 检查是否已登录
    if request.get_cookie("anyShare", secret="<5}>h~1RU4EXP87") != "true":
        app_logger.warning(f"Unauthorized admin stats access attempt. Client-IP: {request.headers.get('x-forwarded-for', request.remote_addr)}")
        return {"status": "error", "message": "unauthorized"}

    # 获取所有文件
    files = get_all_files()
    app_logger.info(f"Admin stats requested, total files: {len(files)}, Client-IP: {request.headers.get('x-forwarded-for', request.remote_addr)}")

    # 计算统计信息
    active_files = len(files)
    total_size = sum(file["file_size"] for file in files)

    # 格式化存储大小
    storage_used = format_size(total_size)
    storage_limit = "2.00 GiB"  # 可以从配置中读取

    # 返回统计信息
    return {"status": "success", "active_files": active_files, "storage_used": storage_used, "storage_limit": storage_limit}
    # 检查是否已登录
    if request.get_cookie("anyShare", secret="<5}>h~1RU4EXP87") != "true":
        return {"status": "error", "message": "unauthorized"}

    # 获取所有文件
    files = get_all_files()

    # 计算统计信息
    active_files = len(files)
    total_size = sum(file["file_size"] for file in files)

    # 格式化存储大小
    storage_used = format_size(total_size)
    storage_limit = "2.00 GiB"  # 可以从配置中读取

    return {"status": "success", "active_files": active_files, "storage_used": storage_used, "storage_limit": storage_limit}


# 登出路由
@app.route("/logout")
def logout():
    """
    用户登出功能。

    通过删除用户的会话cookie来实现登出功能, 然后重定向用户到登录页面。
    """
    app_logger.info(f"User logged out, Client-IP: {request.headers.get('x-forwarded-for', request.remote_addr)}")
    response.delete_cookie("anyShare", path="/")
    # 重定向用户到登录页面
    return redirect("/login")


# 定义删除文件的路由和方法
@app.route("/delete/<file_hash>", method="POST")
def delete_file(file_hash):
    """
    删除指定文件

    检查用户是否具有删除文件的权限，如果用户没有权限，则返回错误信息。
    使用文件哈希值来查找和删除文件。如果文件不存在，则返回错误信息。
    尝试从文件系统和数据库中删除文件。如果删除成功，则返回成功信息。

    参数:
    file_hash (str): 文件的哈希值，用于唯一标识文件。

    返回:
    dict: 包含操作状态和可选的错误消息。
    """
    # 检查用户是否具有删除文件的权限
    if request.get_cookie("anyShare", secret="<5}>h~1RU4EXP87") != "true":
        app_logger.warning(f"Unauthorized file delete attempt: {file_hash}, Client-IP: {request.headers.get('x-forwarded-for', request.remote_addr)}")
        return {"status": "error", "message": "unauthorized"}

    # 获取文件信息
    file_info = get_file(file_hash)
    if not file_info:
        app_logger.warning(f"Attempt to delete non-existent file: {file_hash}, Client-IP: {request.headers.get('x-forwarded-for', request.remote_addr)}")
        return {"status": "error", "message": "file does not exist"}

    # 删除文件
    try:
        # 从文件系统中删除
        file_path = os.path.join(UPLOAD_FOLDER, file_info["file_id"])
        if os.path.exists(file_path):
            os.remove(file_path)
            app_logger.info(f"File deleted from filesystem: '{file_info['file_name']}', hash: {file_hash}, Client-IP: {request.headers.get('x-forwarded-for', request.remote_addr)}")

        # 从数据库中删除
        delete_file_from_db(file_hash)
        app_logger.info(f"File record deleted from database: '{file_info['file_name']}', hash: {file_hash}, Client-IP: {request.headers.get('x-forwarded-for', request.remote_addr)}")

        return {"status": "success"}
    except Exception as e:
        app_logger.error(f"File deletion failed: '{file_info['file_name']}', hash: {file_hash}, error: {str(e)}, Client-IP: {request.headers.get('x-forwarded-for', request.remote_addr)}")
        return {"status": "error", "message": str(e)}


# 辅助函数：格式化文件大小
def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KiB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MiB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GiB"


# 辅助函数：获取相对时间描述
def get_relative_time(date):
    now = datetime.now(timezone.utc)
    diff = now - date if date < now else date - now

    seconds = diff.total_seconds()

    if seconds < 60:
        return "Just now" if date < now else "About to expire"

    minutes = seconds // 60
    if minutes < 60:
        return f"{int(minutes)} minutes {'before' if date < now else 'after'}"

    hours = minutes // 60
    if hours < 24:
        return f"{int(hours)} hours {'before' if date < now else 'after'}"

    days = hours // 24
    if days < 30:
        return f"{int(days)} days {'before' if date < now else 'after'}"

    months = days // 30
    if months < 12:
        return f"{int(months)} months {'before' if date < now else 'after'}"

    years = months // 12
    return f"{int(years)} years {'before' if date < now else 'after'}"


# API接口: 获取文件上传大小限制
@app.route("/api/config", method="GET")
def get_config():
    """
    返回当前系统配置的文件上传大小限制。

    :return: 包含文件大小限制信息的字典，单位为字节。
    """
    app_logger.debug("Config endpoint accessed")
    return {"file_size_limit": float(FILE_LIMIT_SIZE)}


@app.route("/api/healthz", method="GET")
def health_check():
    """
    执行健康检查。

    通过此函数, 服务提供了一个API端点, 用于远程客户端检查服务的运行状态。
    该端点使用GET方法访问, 无需任何参数。

    Returns:
        dict: 包含服务状态的字典，状态为"ok"表示服务正常运行。
    """
    app_logger.debug("Health check endpoint accessed")
    return {"status": "ok"}


if __name__ == "__main__":
    # 创建格式化器
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # 控制台日志处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 文件日志处理器
    file_handler = TimedRotatingFileHandler(filename=os.path.join(LOG_FOLDER, "anyshare.log"), when="midnight", interval=1, backupCount=7, encoding="utf-8", utc=False, delay=False)
    file_handler.suffix = "%Y-%m-%d.log"  # 设置文件名后缀为日期格式
    file_handler.setFormatter(formatter)

    # 配置根日志器
    root_logger = logging.getLogger()
    # 清除可能存在的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # 配置 Waitress 日志器, waitress package 本身定义的也是该日志器
    waitress_logger = logging.getLogger("waitress")
    waitress_logger.propagate = False  # 防止日志向上传递到根日志器
    waitress_logger.setLevel(logging.INFO)
    waitress_logger.addHandler(console_handler)
    waitress_logger.addHandler(file_handler)

    # 配置应用日志器
    app_logger = logging.getLogger("anyshare")
    app_logger.propagate = False  # 防止日志向上传递到根日志器
    app_logger.setLevel(logging.INFO)
    app_logger.addHandler(console_handler)
    app_logger.addHandler(file_handler)

    # 记录应用启动信息
    app_logger.info("=============== AnyShare 文件分享服务启动 ===============")
    app_logger.info(f"上传文件夹: {os.path.abspath(UPLOAD_FOLDER)}")
    app_logger.info(f"日志文件夹: {os.path.abspath(LOG_FOLDER)}")
    app_logger.info(f"文件大小限制: {FILE_LIMIT_SIZE} MiB")
    app_logger.info(f"匿名访问: {'启用' if ANONYMOUS == 'true' else '禁用'}")

    # 启动服务器
    trusted_proxy_headers = ["X-Forwarded-For", "X-Forwarded-Proto", "X-Forwarded-Host", "X-Forwarded-Port"]
    serve(app, host="0.0.0.0", port=80, channel_timeout=60, ident="[AnyShare]", threads=4, trusted_proxy="*", trusted_proxy_count=5, trusted_proxy_headers=trusted_proxy_headers)
