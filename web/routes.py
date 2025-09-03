import os
from datetime import datetime

from bottle import Bottle, redirect, request, response, static_file, template

from config import Config
from services.chunk_upload_service import (
    cancel_chunk_upload,
    complete_chunk_upload,
    create_chunk_upload_session,
    get_chunk_upload_status,
    upload_chunk,
)
from services.database_service import (
    get_file,
    get_user,
    get_user_files,
)
from services.database_service import (
    update_downloads as db_update_downloads,
)
from services.file_service import delete_file, download_file, update_file_expiry, upload_file
from services.logger_service import get_logger
from services.system_service import (
    calculate_statistics,
    format_size,
    get_relative_time,
    get_system_config,
    update_system_config,
)
from services.user_service import (
    add_user as service_add_user,
)
from services.user_service import (
    authenticate_user,
    change_password,
)
from services.user_service import (
    delete_user as service_delete_user,
)
from services.user_service import (
    get_all_users as service_get_all_users,
)

# 创建Bottle应用
app = Bottle()

config = Config()
app_logger = get_logger()


# HTTP错误处理路由 - 使用通配符处理所有4xx和5xx错误
@app.error(400)
def error_4xx(error):
    """
    处理所有4xx客户端错误

    Args:
        error: 错误对象

    Returns:
        渲染的4xx错误页面
    """
    status_code = error.status_code if hasattr(error, "status_code") else 400
    error_messages = {
        400: "400 Bad Request - 请求格式错误",
        401: "401 Unauthorized - 未授权访问",
        403: "403 Forbidden - 禁止访问",
        404: "404 Not Found - 页面未找到",
        405: "405 Method Not Allowed - 请求方法不允许",
        408: "408 Request Timeout - 请求超时",
        413: "413 Payload Too Large - 请求体过大",
        414: "414 URI Too Long - 请求URI过长",
        415: "415 Unsupported Media Type - 不支持的媒体类型",
        429: "429 Too Many Requests - 请求过于频繁",
    }
    message = error_messages.get(status_code, f"{status_code} Client Error - 客户端错误")
    app_logger.warning(
        f"{status_code} Client Error: {error.body}, Client-IP: {request.headers.get('x-forwarded-for', request.remote_addr)}"
    )
    return template("views/error.html", message=message)


@app.error(500)
def error_5xx(error):
    """
    处理所有5xx服务器错误

    Args:
        error: 错误对象

    Returns:
        渲染的5xx错误页面
    """
    status_code = error.status_code if hasattr(error, "status_code") else 500
    error_messages = {
        500: "500 Internal Server Error - 服务器内部错误",
        501: "501 Not Implemented - 功能未实现",
        502: "502 Bad Gateway - 网关错误",
        503: "503 Service Unavailable - 服务不可用",
        504: "504 Gateway Timeout - 网关超时",
        505: "505 HTTP Version Not Supported - HTTP版本不支持",
    }
    message = error_messages.get(status_code, f"{status_code} Server Error - 服务器错误")
    app_logger.error(
        f"{status_code} Server Error: {error.body}, Client-IP: {request.headers.get('x-forwarded-for', request.remote_addr)}"
    )
    return template("views/error.html", message=message)


# 添加404错误处理(Bottle默认不处理404)
@app.error(404)
def error_404(error):
    """
    处理404 Not Found错误

    Args:
        error: 错误对象

    Returns:
        渲染的404错误页面
    """
    app_logger.warning(
        f"404 Not Found error: {error.body}, Client-IP: {request.headers.get('x-forwarded-for', request.remote_addr)}"
    )
    return template("views/error.html", message="404 Not Found - 页面未找到")


# 静态文件路由
@app.route("/static/<filepath:path>")
def server_static(filepath):
    """
    提供静态文件下载服务

    本路由用于访问项目中的静态资源, 如CSS、JavaScript文件和图片等
    它允许Web客户端通过URL请求特定的静态文件

    参数:
    - filepath: 要访问的静态文件路径, 是一个动态参数, 可以匹配多层路径

    返回:
    - static_file对象, 根据给定的文件路径和根目录返回相应的静态文件
    """
    app_logger.debug(f"Static file requested: {filepath}")
    return static_file(filepath, root="./static")


# 主页路由装饰器, 将根路径 "/" 关联到 index 函数
@app.route("/")
def index():
    """
    主页处理函数。

    检查用户是否已经以匿名方式登录, 如果已匿名登录或通过cookie验证, 则渲染主页模板。
    否则, 重定向到登录页面。
    """
    # 从cookie中获取用户名并验证登陆和匿名登陆情况
    username = request.get_cookie("username", secret=config.COOKIE_SECRET) or "anonymous"
    upload_ip = request.headers.get("x-forwarded-for", request.remote_addr)

    # 确定用户角色
    if username == "anonymous":
        user_role = "anonymous"
    else:
        user_info = get_user(username)
        if user_info and user_info["is_admin"] == 1:
            user_role = "admin"
        else:
            user_role = "user"

    if username == "anonymous" and config.ANONYMOUS == "true":
        app_logger.info(f"Index page accessed, user is anonymous, Client-IP: {upload_ip}")
        return template("views/index.html", file_limit_size=config.FILE_LIMIT_SIZE, user_role=user_role)
    elif username == "anonymous" and config.ANONYMOUS == "false":
        app_logger.info(
            f"Index page accessed, user is anonymous,  Client-IP: {upload_ip}, Anonymous login is prohibited, redirect to login."
        )
        return redirect("/login")
    else:
        app_logger.info(f"Index page accessed, {username} is logged in, Client-IP: {upload_ip}")
        return template("views/index.html", file_limit_size=config.FILE_LIMIT_SIZE, user_role=user_role)


# 管理员登录页面
@app.route("/login")
def login_page():
    """
    渲染并返回登录页面。

    该函数通过装饰器@app.route("/login")与URL路径/login关联
    当访问该路径时, bottle框架将调用此函数。

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
    用户登录验证函数。

    该函数首先从请求中获取用户名和密码, 然后验证用户凭据。
    如果验证成功, 设置会话cookie并重定向到适当的页面; 否则返回登录页面并显示错误信息。
    """
    # 获取登录表单中的用户名和密码
    username = request.forms.get("username")
    password = request.forms.get("password")

    # 获取客户端IP
    client_ip = request.headers.get("x-forwarded-for", request.remote_addr)

    # 调用用户服务模块进行认证
    result = authenticate_user(username, password, client_ip)
    if result["status"] == "success":
        user = result["user"]
        # 设置会话cookie
        response.set_cookie("username", username, secret=config.COOKIE_SECRET, path="/")

        # 根据用户角色重定向到适当的页面
        if user["is_admin"] == 1:
            return redirect("/admin")
        else:
            return redirect("/myfiles")
    else:
        return template("views/login.html", error=result["message"])


# 处理文件上传, 并在服务端验证文件大小限制(防止用户前端修改css脚本实现文件大小限制解除), 并返回文件信息
@app.route("/upload", method="POST")
def upload():
    """
    处理文件上传请求。

    此函数首先检查用户是否已登录或匿名登录。如果未满足登录条件, 则返回未经授权的错误。
    接着, 函数会检查上传的文件是否存在, 计算文件大小, 并验证是否超过允许的最大大小。
    如果文件过大, 将删除文件并返回错误信息。
    最后, 函数会根据用户选择的过期时间选项, 计算文件的过期日期, 并将文件信息保存到数据库。

    Returns:
        dict: 包含上传状态、文件ID、文件哈希、文件名、大小、过期选项、密码和上传IP的信息。
    """
    # 从cookie中获取用户名并验证上传文件权限情况
    username = request.get_cookie("username", secret=config.COOKIE_SECRET) or "anonymous"
    # 获取客户端IP(支持反向代理)
    upload_ip = request.headers.get("x-forwarded-for", request.remote_addr)

    # 获取用户信息
    user_info = get_user(username) if username != "anonymous" else {"username": "anonymous"}

    if username == "anonymous" and config.ANONYMOUS == "false":
        app_logger.warning(f"Unauthorized upload attempt from IP: {upload_ip}")
        return {"status": "error", "message": "unauthorized"}
    elif username == "anonymous" and config.ANONYMOUS == "true":
        app_logger.info(f"Anonymous upload attempt, Client-IP: {upload_ip}")
    else:
        app_logger.info(f"{username} are uploading file, Client-IP: {upload_ip}")

    upload_file_data = request.files.get("file")

    # 调用文件服务模块处理上传
    result = upload_file(upload_file_data, user_info, upload_ip, config.FILE_LIMIT_SIZE, config.UPLOAD_FOLDER)
    return result


# 处理文件上传成功后的页面逻辑
@app.route("/upload", method="GET")
def upload_success():
    """
    检查用户登录状态, 如果未登录或未匿名登录, 则重定向到登录页面。
    如果提供了文件信息, 则解析文件信息并渲染上传成功的页面; 否则重定向到主页。
    """
    # 从cookie中获取用户名并验证上传文件权限情况
    username = request.get_cookie("username", secret=config.COOKIE_SECRET) or "anonymous"
    # 获取URL参数中的文件信息字符串
    file_hash = request.query.get("file_hash")
    # 获取客户端IP(支持反向代理)
    upload_ip = request.headers.get("x-forwarded-for", request.remote_addr)
    if file_hash:
        if username == "anonymous" and config.ANONYMOUS == "false":
            app_logger.warning(f"Unauthorized attempt to access upload page from IP: {upload_ip}")
            return {"status": "error", "message": "unauthorized"}
        elif username == "anonymous" and config.ANONYMOUS == "true":
            app_logger.info(f"Anonymous access to upload page from IP: {upload_ip}")
        else:
            app_logger.info(f"{username} access to upload page from IP: {upload_ip}")

    # 如果没有文件hash信息, 则重定向到主页
    else:
        return redirect("/")

    # 确定用户角色
    if username == "anonymous":
        user_role = "anonymous"
    else:
        user_info = get_user(username)
        if user_info and user_info["is_admin"] == 1:
            user_role = "admin"
        else:
            user_role = "user"

    try:
        file_info = get_file(file_hash)
        # 直接使用解析后的文件信息渲染模板
        return template("views/upload.html", file_info=file_info, user_role=user_role)
    except Exception as e:
        # 如果解析文件信息时发生错误, 渲染错误页面
        return template("error.html", error=f"Error parsing file information: {str(e)}")


# 获取文件信息
@app.route("/file")
def get_file_info():
    """
    根据文件哈希和密码获取文件信息。
    从请求查询中获取文件哈希和密码, 验证文件是否存在和有效, 以及密码是否正确。
    如果文件不存在或已过期, 显示错误信息。如果密码正确, 提供文件下载。
    如果未提供密码或密码错误, 提示用户输入正确的密码。
    """
    # 从查询参数中获取文件哈希和密码
    file_hash = request.query.get("hash")
    password = request.query.get("pwd")

    # 如果没有文件哈希, 则重定向到主页
    if not file_hash:
        app_logger.warning("File info requested without hash, redirect to index.")
        return redirect("/login")

    # 获取客户端IP
    client_ip = request.headers.get("x-forwarded-for", request.remote_addr)

    # 检查是否需要更新下载次数
    update_download_count = request.headers.get("X-Update-Download-Count") == "true"

    # 调用文件服务模块处理下载
    # 对于分片下载, 通过X-Update-Download-Count头部控制; 对于传统下载, 在路由中处理
    result = download_file(file_hash, password, client_ip, config.UPLOAD_FOLDER, update_download_count=False)

    if result["status"] == "success":
        file_on_disk = os.path.basename(result["file_path"])

        # 支持断点续传的文件下载
        file_path = result["file_path"]
        file_name = result["file_name"]

        # 获取文件大小
        file_size = os.path.getsize(file_path)

        # 检查是否是HEAD请求
        if request.method == "HEAD":
            # 只返回头部信息
            app_logger.info(f"HEAD request for file: {file_name}, size: {file_size}, Client-IP: {client_ip}")
            response.headers["Content-Length"] = str(file_size)
            response.headers["Content-Type"] = "application/octet-stream"
            response.headers["Content-Disposition"] = f'attachment; filename="{file_name}"'
            response.headers["Accept-Ranges"] = "bytes"
            return ""

        # 检查是否有Range请求头(断点续传)
        range_header = request.headers.get("Range")

        if range_header:
            # 解析Range头
            try:
                range_match = range_header.replace("bytes=", "").split("-")
                start = int(range_match[0]) if range_match[0] else 0
                end = int(range_match[1]) if range_match[1] else file_size - 1

                app_logger.info(
                    f"Range request for file: {file_name}, range: {start}-{end}/{file_size}, Client-IP: {client_ip}"
                )

                # 验证范围
                if start >= file_size or end >= file_size or start > end:
                    response.status = 416  # Range Not Satisfiable
                    response.headers["Content-Range"] = f"bytes */{file_size}"
                    return "Range Not Satisfiable"

                # 设置响应头
                response.status = 206  # Partial Content
                response.headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
                response.headers["Accept-Ranges"] = "bytes"
                response.headers["Content-Length"] = str(end - start + 1)
                response.headers["Content-Type"] = "application/octet-stream"
                response.headers["Content-Disposition"] = f'attachment; filename="{file_name}"'

                # 读取指定范围的文件内容
                def generate_partial_content():
                    with open(file_path, "rb") as f:
                        f.seek(start)
                        remaining = end - start + 1
                        while remaining > 0:
                            chunk_size = min(8192, remaining)
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            remaining -= len(chunk)
                            yield chunk

                return generate_partial_content()

            except (ValueError, IndexError):
                # Range头格式错误, 返回完整文件
                pass

        # 返回完整文件
        # 如果是完整下载(非HEAD请求且没有Range头), 则更新下载次数
        # 或者如果是分片下载的最终请求(有X-Update-Download-Count头部), 也更新下载次数
        if (request.method != "HEAD" and not range_header) or update_download_count:
            db_update_downloads(file_hash)
            if update_download_count:
                app_logger.info(
                    f"Chunked download completed for file: {file_name}, hash: {file_hash}, Client-IP: {client_ip}"
                )
            else:
                app_logger.info(
                    f"Full download completed for file: {file_name}, hash: {file_hash}, Client-IP: {client_ip}"
                )

        return static_file(file_on_disk, root=config.UPLOAD_FOLDER, download=file_name)
    elif result["status"] == "password_required":
        # 确定用户角色
        username = request.get_cookie("username", secret=config.COOKIE_SECRET) or "anonymous"
        if username == "anonymous":
            user_role = "anonymous"
        else:
            user_info = get_user(username)
            if user_info and user_info["is_admin"] == 1:
                user_role = "admin"
            else:
                user_role = "user"
        return template("views/password.html", file_hash=file_hash, error=None, user_role=user_role)
    elif result["status"] == "error":
        if "password error" in result["message"]:
            # 确定用户角色
            username = request.get_cookie("username", secret=config.COOKIE_SECRET) or "anonymous"
            if username == "anonymous":
                user_role = "anonymous"
            else:
                user_info = get_user(username)
                if user_info and user_info["is_admin"] == 1:
                    user_role = "admin"
                else:
                    user_role = "user"
            return template("views/password.html", file_hash=file_hash, error="password error", user_role=user_role)
        else:
            return template("views/error.html", message=result["message"])
    else:
        return template("views/error.html", message="Unknown error occurred")


# 处理密码提交
@app.route("/verify", method="POST")
def verify_password():
    """
    验证密码并重定向到对应的文件下载页面。

    该函数通过POST请求获取用户提交的文件哈希值和密码, 然后检查这些信息是否完整。
    如果任一信息缺失, 将返回错误页面。否则, 将用户重定向到带有密码的文件链接。
    """
    # 获取用户提交的文件哈希值和密码
    file_hash = request.forms.get("hash")
    password = request.forms.get("password")

    # 检查文件哈希值和密码是否都已提供
    if not file_hash or not password:
        # 返回错误页面, 提示参数错误
        return template("views/error.html", message="parameter error")

    # 重定向到带密码的文件链接
    return redirect(f"/file?hash={file_hash}&pwd={password}")


# 授权用户页面路由
@app.route("/admin")
def admin_page():
    """
    管理员页面路由。
    检查用户是否已登录且是管理员, 如果不是则重定向到登录页面。
    获取所有文件信息, 格式化时间, 然后渲染管理员页面模板。
    """
    # 从cookie中获取用户名并验证上传文件权限情况
    username = request.get_cookie("username", secret=config.COOKIE_SECRET) or "anonymous"
    # 获取客户端IP(支持反向代理)
    upload_ip = request.headers.get("x-forwarded-for", request.remote_addr)
    # 获取用户信息
    user_info = get_user(username)

    if user_info and user_info["is_admin"]:
        app_logger.info(f"{username} access admin page from IP: {upload_ip}")
    else:
        app_logger.warning(f"Non-admin user {username} attempted to access admin page from IP: {upload_ip}")
        return template("views/error.html", message="You do not have permission to access this page")

    # 获取所有文件
    files = get_user_files(username)
    app_logger.info(
        f"Admin page requested, total files: {len(files)}, Client-IP: {request.headers.get('x-forwarded-for', request.remote_addr)}"
    )

    # 计算统计信息
    active_files = len(files)
    total_size = sum(file["file_size"] for file in files)

    # 格式化存储大小
    storage_used = format_size(total_size)
    storage_limit = f"{config.USER_LIMIT_SIZE} GiB"  # 可以从配置中读取

    # 格式化时间和存储空间
    for file in files:
        # 上传时间
        upload_date = file["upload_date"]
        # 如果upload_date是字符串, 则先转换为datetime对象
        if isinstance(upload_date, str):
            upload_date = datetime.fromisoformat(upload_date.replace("Z", "+00:00"))
        file["upload_formatted"] = upload_date.strftime("%Y-%m-%d %H:%M:%S")
        file["upload_relative"] = get_relative_time(upload_date)

        # 过期时间
        expiry_date = file["expiry_date"]
        # 如果expiry_date是字符串, 则先转换为datetime对象
        if isinstance(expiry_date, str):
            expiry_date = datetime.fromisoformat(expiry_date.replace("Z", "+00:00"))
        file["expiry_formatted"] = expiry_date.strftime("%Y-%m-%d %H:%M:%S")
        file["expiry_relative"] = get_relative_time(expiry_date)

        # 格式化存储空间
        file["size_formatted"] = format_size(file["file_size"])

    # 编译统计信息字典
    stats = {
        "active_files": active_files,
        "storage_used": storage_used,
        "storage_limit": storage_limit,
        "anonymous_enabled": config.ANONYMOUS,
        "file_limit_size": config.FILE_LIMIT_SIZE,
    }

    # 渲染管理员页面模板
    return template("views/admin.html", files=files, stats=stats, user_role="admin")


# 获取管理统计数据
@app.route("/admin/stats")
def get_admin_stats_route():
    """
    获取授权用户的管理统计信息的路由处理函数。
    检查用户是否已登录, 然后计算和返回文件统计信息。

    Returns:
        dict: 包含统计信息的字典, 如活跃文件数和存储使用情况。
    """
    # 从cookie中获取用户名并验证上传文件权限情况
    username = request.get_cookie("username", secret=config.COOKIE_SECRET) or "anonymous"
    # 获取客户端IP(支持反向代理)
    upload_ip = request.headers.get("x-forwarded-for", request.remote_addr)
    if username == "anonymous":
        app_logger.warning(f"Unauthorized admin stats access attempt. Client-IP: {upload_ip}")
        return {"status": "error", "message": "unauthorized"}
    else:
        app_logger.info(f"{username} access admin stats, Client-IP: {upload_ip}")

    # 调用系统服务模块计算统计信息
    result = calculate_statistics(username)

    # 添加存储限制信息
    result["storage_limit"] = f"{config.USER_LIMIT_SIZE} GiB"

    return result


# 获取所有用户列表
@app.route("/admin/users")
def get_all_users_list():
    """
    获取所有用户列表的路由处理函数。
    只有管理员可以访问此端点。

    Returns:
        dict: 包含用户列表的字典。
    """
    # 从cookie中获取用户名并验证权限
    username = request.get_cookie("username", secret=config.COOKIE_SECRET) or "anonymous"
    # 获取客户端IP(支持反向代理)
    client_ip = request.headers.get("x-forwarded-for", request.remote_addr)

    # 检查用户是否已登录
    if not username or username == "anonymous":
        app_logger.warning(f"Unauthorized attempt to access users list from IP: {client_ip}")
        return {"status": "error", "message": "unauthorized"}

    # 检查用户是否为管理员
    user_info = get_user(username)

    # 调用用户服务模块获取所有用户
    result = service_get_all_users(user_info, client_ip)
    return result


# 登出路由
@app.route("/logout")
def logout():
    """
    用户登出功能。

    通过删除用户的会话cookie来实现登出功能, 然后重定向用户到登录页面。
    """
    # 从cookie中获取用户名并验证上传文件权限情况
    username = request.get_cookie("username", secret=config.COOKIE_SECRET) or "anonymous"
    # 获取客户端IP(支持反向代理)
    upload_ip = request.headers.get("x-forwarded-for", request.remote_addr)
    if username != "anonymous":
        # 删除用户会话cookie
        response.delete_cookie("username", secret=config.COOKIE_SECRET)
    app_logger.info(f"{username} logged out, Client-IP: {upload_ip}")
    # 重定向用户到登录页面
    return redirect("/login")


# 定义删除文件的路由和方法
@app.route("/delete/<file_hash>", method="POST")
def delete_file_route(file_hash):
    """
    删除指定文件

    检查用户是否具有删除文件的权限, 如果用户没有权限, 则返回错误信息。
    使用文件哈希值来查找和删除文件。如果文件不存在, 则返回错误信息。
    尝试从文件系统和数据库中删除文件。如果删除成功, 则返回成功信息。

    参数:
    file_hash (str): 文件的哈希值, 用于唯一标识文件。

    返回:
    dict: 包含操作状态和可选的错误消息。
    """
    # 从cookie中获取用户名并验证上传文件权限情况
    username = request.get_cookie("username", secret=config.COOKIE_SECRET) or "anonymous"
    # 获取客户端IP(支持反向代理)
    client_ip = request.headers.get("x-forwarded-for", request.remote_addr)

    # 获取用户信息
    user_info = get_user(username) if username != "anonymous" else {"username": "anonymous"}

    # 调用文件服务模块处理删除
    result = delete_file(file_hash, user_info, client_ip)
    return result


# 用户管理页面
# 添加用户
@app.route("/users/add", method="POST")
def add_user_route():
    """
    添加用户路由。
    检查用户是否已登录且是管理员, 然后处理添加用户的请求。
    """
    # 从cookie中获取用户名并验证上传文件权限情况
    username = request.get_cookie("username", secret=config.COOKIE_SECRET) or "anonymous"
    # 获取客户端IP(支持反向代理)
    client_ip = request.headers.get("x-forwarded-for", request.remote_addr)

    # 如果用户是匿名用户, 直接返回错误
    if username == "anonymous":
        app_logger.warning(f"Anonymous user attempted to access users admin page from IP: {client_ip}")
        return template("views/error.html", message="You do not have permission to access this page")

    # 获取用户信息
    user_info = get_user(username)
    # 获取表单数据
    new_username = request.forms.get("username")
    password = request.forms.get("password")
    # 强制设置为普通用户, 不允许添加管理员账户
    is_admin = 0

    # 调用用户服务模块添加用户
    result = service_add_user(user_info, new_username, password, is_admin, client_ip)

    if result["status"] == "success":
        return redirect("/admin")
    else:
        app_logger.warning(f"Failed to add user {new_username} by admin {username}, Client-IP: {client_ip}")
        return redirect("/admin")


# 删除用户
@app.route("/users/delete", method="POST")
def delete_user_route():
    """
    删除用户路由。
    检查用户是否已登录且是管理员, 然后处理删除用户的请求。
    """
    # 从cookie中获取用户名并验证上传文件权限情况
    username = request.get_cookie("username", secret=config.COOKIE_SECRET) or "anonymous"
    # 获取客户端IP(支持反向代理)
    client_ip = request.headers.get("x-forwarded-for", request.remote_addr)
    # 获取用户信息
    user_info = get_user(username)

    # 获取要删除的用户名
    username_delete = request.forms.get("username")

    # 调用用户服务模块删除用户
    result = service_delete_user(user_info, username_delete, client_ip)
    return result


# 更新文件过期时间
@app.route("/update_expiry", method="POST")
def update_expiry_route():
    """
    更新文件过期时间路由。
    检查用户是否已登录且是管理员, 然后处理更新文件过期时间的请求。
    """
    # 检查是否已登录
    username = request.get_cookie("username", secret=config.COOKIE_SECRET)
    if not username:
        return {"status": "error", "message": "unauthorized"}

    # 获取用户信息
    user = get_user(username)
    if not user:
        return {"status": "error", "message": "permission denied"}

    # 获取表单数据
    file_hash = request.forms.get("file_hash")
    expiry_option = request.forms.get("expiry")

    if not file_hash or not expiry_option:
        return {"status": "error", "message": "missing parameters"}

    # 获取客户端IP
    client_ip = request.headers.get("x-forwarded-for", request.remote_addr)

    # 调用文件服务模块更新过期时间
    result = update_file_expiry(file_hash, expiry_option, user, client_ip)
    return result


# 修改用户密码
@app.route("/users/change_password", method="POST")
def change_password_route():
    """
    修改用户密码路由。
    管理员可以修改所有用户密码, 普通用户只能修改自己密码。
    """
    # 检查是否已登录
    current_user = request.get_cookie("username", secret=config.COOKIE_SECRET)
    if not current_user or current_user == "anonymous":
        return {"status": "error", "message": "unauthorized"}

    # 获取用户信息
    current_user_info = get_user(current_user)
    if not current_user_info:
        return {"status": "error", "message": "permission denied"}

    # 获取表单数据
    target_user = request.forms.get("username")
    new_password = request.forms.get("new_password")

    if not target_user or not new_password:
        return {"status": "error", "message": "missing parameters"}

    # 获取客户端IP
    client_ip = request.headers.get("x-forwarded-for", request.remote_addr)

    # 调用用户服务模块修改密码
    result = change_password(current_user_info, target_user, new_password, client_ip)
    return result


# 更新系统配置
@app.route("/admin/config", method="POST")
def update_config_route():
    """
    更新系统配置路由。
    只有管理员可以访问。
    """
    # 检查是否已登录
    username = request.get_cookie("username", secret=config.COOKIE_SECRET)
    if not username or username == "anonymous":
        return {"status": "error", "message": "unauthorized"}

    # 获取用户信息
    user = get_user(username)
    if not user or user["is_admin"] != 1:
        return {"status": "error", "message": "permission denied"}

    # 获取表单数据
    anonymous = request.forms.get("anonymous")
    file_limit_size = request.forms.get("file_limit_size")

    # 获取客户端IP
    client_ip = request.headers.get("x-forwarded-for", request.remote_addr)

    # 调用系统服务模块更新配置
    result = update_system_config(user, anonymous, file_limit_size, client_ip)

    # 更新环境变量(在实际应用中, 可能需要保存到配置文件或数据库)
    if anonymous is not None:
        config.ANONYMOUS = anonymous
    if file_limit_size is not None:
        config.FILE_LIMIT_SIZE = file_limit_size

    return result


# 获取系统配置
@app.route("/admin/config", method="GET")
def get_config_route():
    """
    获取系统配置路由。
    只有管理员可以访问。
    """
    # 检查是否已登录
    username = request.get_cookie("username", secret=config.COOKIE_SECRET)
    if not username or username == "anonymous":
        return {"status": "error", "message": "unauthorized"}

    # 获取用户信息
    user = get_user(username)
    if not user or user["is_admin"] != 1:
        return {"status": "error", "message": "permission denied"}

    # 调用系统服务模块获取配置
    result = get_system_config(config.ANONYMOUS, config.FILE_LIMIT_SIZE, config.USER_LIMIT_SIZE)
    return result


# API接口: 获取文件上传大小限制
@app.route("/api/config", method="GET")
def api_get_config():
    """
    返回当前系统配置的文件上传大小限制。

    :return: 包含文件大小限制信息的字典, 单位为字节。
    """
    app_logger.debug("Config endpoint accessed")
    return {"file_size_limit": float(config.FILE_LIMIT_SIZE)}


# 分片上传相关路由
@app.route("/api/chunk/session", method="POST")
def create_chunk_session():
    """
    创建分片上传会话
    """
    # 验证用户权限
    username = request.get_cookie("username", secret=config.COOKIE_SECRET) or "anonymous"
    client_ip = request.headers.get("x-forwarded-for", request.remote_addr)

    if username == "anonymous" and config.ANONYMOUS == "false":
        app_logger.warning(f"Unauthorized chunk upload attempt from IP: {client_ip}")
        return {"status": "error", "message": "unauthorized"}

    # 获取用户信息
    user_info = get_user(username) if username != "anonymous" else {"username": "anonymous"}

    # 获取请求参数
    file_name = request.forms.get("file_name")
    file_size = request.forms.get("file_size")
    chunk_size = request.forms.get("chunk_size")

    if not file_name or not file_size:
        return {"status": "error", "message": "Missing required parameters"}

    try:
        file_size = int(file_size)
        chunk_size = int(chunk_size) if chunk_size else None

        # 检查文件大小限制
        max_size_bytes = float(config.FILE_LIMIT_SIZE) * 1024 * 1024
        if file_size > max_size_bytes:
            return {"status": "error", "message": f"File size over the limit of {config.FILE_LIMIT_SIZE} MiB"}

        # 创建分片上传会话
        result = create_chunk_upload_session(file_name, file_size, user_info, client_ip, chunk_size)
        return result

    except ValueError:
        return {"status": "error", "message": "Invalid file size or chunk size"}


@app.route("/api/chunk/upload", method="POST")
def upload_chunk_route():
    """
    上传文件分片
    """
    # 验证用户权限
    username = request.get_cookie("username", secret=config.COOKIE_SECRET) or "anonymous"
    client_ip = request.headers.get("x-forwarded-for", request.remote_addr)

    if username == "anonymous" and config.ANONYMOUS == "false":
        return {"status": "error", "message": "unauthorized"}

    # 获取用户信息
    user_info = get_user(username) if username != "anonymous" else {"username": "anonymous"}

    # 获取请求参数
    session_id = request.forms.get("session_id")
    chunk_index = request.forms.get("chunk_index")
    chunk_file = request.files.get("chunk")

    if not session_id or chunk_index is None or not chunk_file:
        return {"status": "error", "message": "Missing required parameters"}

    try:
        chunk_index = int(chunk_index)
        chunk_data = chunk_file.file.read()

        # 上传分片
        result = upload_chunk(session_id, chunk_index, chunk_data, user_info, client_ip)
        return result

    except ValueError:
        return {"status": "error", "message": "Invalid chunk index"}


@app.route("/api/chunk/complete", method="POST")
def complete_chunk_upload_route():
    """
    完成分片上传
    """
    # 验证用户权限
    username = request.get_cookie("username", secret=config.COOKIE_SECRET) or "anonymous"
    client_ip = request.headers.get("x-forwarded-for", request.remote_addr)

    if username == "anonymous" and config.ANONYMOUS == "false":
        return {"status": "error", "message": "unauthorized"}

    # 获取用户信息
    user_info = get_user(username) if username != "anonymous" else {"username": "anonymous"}

    # 获取请求参数
    session_id = request.forms.get("session_id")
    expiry_option = request.forms.get("expiry_option", "1 day")

    if not session_id:
        return {"status": "error", "message": "Missing session_id"}

    # 完成分片上传
    result = complete_chunk_upload(session_id, user_info, client_ip, config.UPLOAD_FOLDER, expiry_option)
    return result


@app.route("/api/chunk/status/<session_id>", method="GET")
def get_chunk_status_route(session_id):
    """
    获取分片上传状态
    """
    # 验证用户权限
    username = request.get_cookie("username", secret=config.COOKIE_SECRET) or "anonymous"
    client_ip = request.headers.get("x-forwarded-for", request.remote_addr)

    if username == "anonymous" and config.ANONYMOUS == "false":
        return {"status": "error", "message": "unauthorized"}

    # 获取用户信息
    user_info = get_user(username) if username != "anonymous" else {"username": "anonymous"}

    # 获取上传状态
    result = get_chunk_upload_status(session_id, user_info, client_ip)
    return result


@app.route("/api/chunk/cancel", method="POST")
def cancel_chunk_upload_route():
    """
    取消分片上传
    """
    # 验证用户权限
    username = request.get_cookie("username", secret=config.COOKIE_SECRET) or "anonymous"
    client_ip = request.headers.get("x-forwarded-for", request.remote_addr)

    if username == "anonymous" and config.ANONYMOUS == "false":
        return {"status": "error", "message": "unauthorized"}

    # 获取用户信息
    user_info = get_user(username) if username != "anonymous" else {"username": "anonymous"}

    # 获取请求参数
    session_id = request.forms.get("session_id")

    if not session_id:
        return {"status": "error", "message": "Missing session_id"}

    # 取消分片上传
    result = cancel_chunk_upload(session_id, user_info, client_ip)
    return result


@app.route("/api/healthz", method="GET")
def health_check_route():
    """
    执行健康检查。

    通过此函数, 服务提供了一个API端点, 用于远程客户端检查服务的运行状态。
    该端点使用GET方法访问, 无需任何参数。

    Returns:
        dict: 包含服务状态的字典, 状态为"ok"表示服务正常运行。
    """
    app_logger.debug("Health check endpoint accessed")
    return {"status": "ok"}


# 用户个人文件页面路由
@app.route("/myfiles")
def my_files_page():
    """
    用户个人文件页面路由。
    检查用户是否已登录, 如果未登录则重定向到登录页面。
    获取用户自己的文件列表, 然后渲染用户文件页面模板。
    """
    # 从cookie中获取用户名并验证上传文件权限情况
    username = request.get_cookie("username", secret=config.COOKIE_SECRET) or "anonymous"
    # 获取客户端IP(支持反向代理)
    upload_ip = request.headers.get("x-forwarded-for", request.remote_addr)
    if username == "anonymous":
        app_logger.warning(f"Unauthorized attempt to access my files page from IP: {upload_ip}")
        return redirect("/login")
    else:
        app_logger.info(f"{username} access my files page from IP: {upload_ip}")

    # 获取用户自己的文件信息
    files = get_user_files(username)
    app_logger.info(f"user files page accessed by {username}, total files: {len(files)}")

    # 格式化时间和存储空间
    for file in files:
        # 上传时间
        upload_date = file["upload_date"]
        # 如果upload_date是字符串, 则先转换为datetime对象
        if isinstance(upload_date, str):
            upload_date = datetime.fromisoformat(upload_date.replace("Z", "+00:00"))
        file["upload_formatted"] = upload_date.strftime("%Y-%m-%d %H:%M:%S")
        file["upload_relative"] = get_relative_time(upload_date)

        # 过期时间
        expiry_date = file["expiry_date"]
        # 如果expiry_date是字符串, 则先转换为datetime对象
        if isinstance(expiry_date, str):
            expiry_date = datetime.fromisoformat(expiry_date.replace("Z", "+00:00"))
        file["expiry_formatted"] = expiry_date.strftime("%Y-%m-%d %H:%M:%S")
        file["expiry_relative"] = get_relative_time(expiry_date)

        # 格式化存储空间
        file["size_formatted"] = format_size(file["file_size"])

    # 渲染用户文件页面模板
    return template("views/myfiles.html", files=files)
