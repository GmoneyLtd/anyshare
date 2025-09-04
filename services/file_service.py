import hashlib
import os
from datetime import UTC, datetime, timedelta

from services.database_service import add_file as db_add_file
from services.database_service import delete_expired_files as db_delete_expired_files
from services.database_service import delete_file_from_db as db_delete_file
from services.database_service import get_file as db_get_file
from services.database_service import update_file_expiry as db_update_file_expiry
from services.logger_service import get_logger
from services.system_service import get_relative_time

app_logger = get_logger()


def upload_file(file_data, user_info, client_ip, file_limit_size, upload_folder, password=None):
    """
    处理文件上传业务逻辑

    Args:
        file_data: 文件数据
        user_info: 用户信息
        client_ip: 客户端IP
        file_limit_size: 文件大小限制
        upload_folder: 上传文件夹路径
        password: 文件密码(可选)

    Returns:
        dict: 包含上传状态和文件信息的字典
    """
    username = user_info.get("username", "anonymous")

    if username == "anonymous":
        app_logger.info(f"Anonymous upload attempt, Client-IP: {client_ip}")
    else:
        app_logger.info(f"{username} are uploading file, Client-IP: {client_ip}")

    if not file_data:
        app_logger.warning("Upload request received without file selection")
        return {"status": "error", "message": "no file is selected"}

    try:
        total_size = 0
        max_size_bytes = float(file_limit_size) * 1024 * 1024
        # 获取文件信息
        # Use raw_filename to get the original, unmodified filename from the browser
        file_name = file_data.raw_filename
        # 构建文件的hash值
        hash_input = f"{file_name}_{datetime.now(UTC).timestamp()}"
        file_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        file_path = os.path.join(upload_folder, file_hash)
        # 处理多个代理IP的情况
        client_ip = client_ip.partition(",")[0].strip()
        # 流式读取文件并计算总大小, 每次读取8KB
        app_logger.info(f"File upload started: '{file_name}', Client-IP: {client_ip}")

        with open(file_path, "wb") as f:
            while True:
                chunk = file_data.file.read(8192)
                if not chunk:
                    break
                f.write(chunk)
                total_size += len(chunk)
                if total_size > max_size_bytes:
                    app_logger.warning(f"File size exceeded limit: '{file_name}', Client-IP: {client_ip}")
                    os.remove(file_path)
                    return {
                        "status": "error",
                        "message": f"File size over the limit of {file_limit_size} MiB",
                    }

        # 默认过期时间1天
        expiry_date = datetime.now(UTC) + timedelta(days=1)

        # 保存到数据库
        password = db_add_file(file_name, file_hash, total_size, expiry_date, client_ip, username, password)

        app_logger.info(
            f"{username}'s file upload has been completed, filename: '{file_name}', hash: {file_hash}, expiry: 1 day, size: {total_size} bytes, Client-IP: {client_ip}"
        )
        return {"status": "success", "file_hash": file_hash, "password": password}
    except Exception as e:
        app_logger.error(
            f"{username}'s file upload failed: '{file_name if 'file_name' in locals() else 'unknown'}', error: {str(e)}"
        )
        if "file_path" in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
                app_logger.warning(f"Partial file removed due to error: {file_path}")
            except Exception as remove_err:
                app_logger.error(f"Failed to remove partial file: {file_path}, error: {str(remove_err)}")
        return {"status": "error", "message": f"An error occurred: {str(e)}"}


def download_file(file_hash, password, client_ip, upload_folder):
    """
    处理文件下载业务逻辑

    Args:
        file_hash: 文件哈希
        password: 文件密码
        client_ip: 客户端IP
        upload_folder: 上传文件夹路径

    Returns:
        dict: 包含下载状态和文件信息的字典
    """
    # 根据文件哈希获取文件信息
    file_info = db_get_file(file_hash)

    # 如果文件信息不存在, 显示错误信息
    if not file_info:
        app_logger.warning(f"Attempt to access non-existent or expired file: {file_hash}, Client-IP: {client_ip}")
        return {"status": "error", "message": "The file does not exist or has expired"}

    # 检查是否过期
    expiry_date = file_info["expiry_date"]
    # 如果expiry_date是字符串, 则先转换为datetime对象
    if isinstance(expiry_date, str):
        expiry_date = datetime.fromisoformat(expiry_date.replace("Z", "+00:00"))
    if expiry_date < datetime.now(UTC):
        app_logger.info(
            f"Attempt to access expired file: {file_hash}, expired on: {expiry_date}, Client-IP: {client_ip}"
        )
        return {"status": "error", "message": "Sharing has expired"}

    # 如果提供了密码, 检查密码是否正确
    if password:
        if password == file_info["password"]:
            # 注意: 这里不再更新下载次数, 下载次数将在文件实际开始传输时更新
            file_path = os.path.join(upload_folder, file_hash)
            if os.path.exists(file_path):
                return {"status": "success", "file_path": file_path, "file_name": file_info["file_name"]}
            else:
                return {"status": "error", "message": "File not found on disk"}
        else:
            app_logger.warning(f"Incorrect password provided for file: {file_hash}, Client-IP: {client_ip}")
            return {"status": "error", "message": "password error"}
            
    app_logger.info(f"File download request received: hash={file_hash}, pwd={password}, Client-IP: {client_ip}")

    return {"status": "password_required", "file_hash": file_hash}


def delete_file(file_hash, user_info, client_ip):
    """
    处理文件删除业务逻辑

    Args:
        file_hash: 文件哈希
        user_info: 用户信息
        client_ip: 客户端IP

    Returns:
        dict: 包含删除状态的字典
    """
    username = user_info.get("username", "anonymous")

    if username == "anonymous":
        app_logger.warning(f"Anonymous user tried to delete a file with {file_hash} from {client_ip}")
        return {"status": "error", "message": "You are not authorized to delete files."}

    file_info = db_get_file(file_hash)
    if not file_info:
        return {"status": "error", "message": "File not found."}

    # 检查权限: 只有文件所有者或管理员才能删除文件
    if file_info["username"] == username or user_info.get("is_admin", 0) == 1:
        # 删除文件
        try:
            # 从文件系统中删除
            file_path = os.path.join("./upload", file_info["file_hash"])
            if os.path.exists(file_path):
                os.remove(file_path)
                app_logger.info(
                    f"File deleted from filesystem: '{file_info['file_name']}', hash: {file_hash}, Client-IP: {client_ip}"
                )

            # 从数据库中删除
            db_delete_file(file_hash)
            app_logger.info(
                f"File record deleted from database: '{file_info['file_name']}', hash: {file_hash}, Client-IP: {client_ip}"
            )

            return {"status": "success"}
        except Exception as e:
            app_logger.error(
                f"File deletion failed: '{file_info['file_name']}', hash: {file_hash}, error: {str(e)}, Client-IP: {client_ip}"
            )
            return {"status": "error", "message": str(e)}
    else:
        app_logger.warning(
            f"User {username} attempted to delete file not owned by them: {file_hash}, Client-IP: {client_ip}"
        )
        return {"status": "error", "message": "permission denied"}


def cleanup_expired_files():
    """
    清理过期文件
    """
    db_delete_expired_files()


def update_file_expiry(file_hash, expiry_option, user_info, client_ip):
    """
    更新文件过期时间

    Args:
        file_hash: 文件哈希
        expiry_option: 过期选项
        user_info: 用户信息
        client_ip: 客户端IP

    Returns:
        dict: 包含更新状态和新过期信息的字典
    """
    username = user_info.get("username")

    # 获取文件信息
    file_info = db_get_file(file_hash)
    if not file_info:
        return {"status": "error", "message": "file not found"}

    # 检查权限: 只有文件所有者或管理员才能更新过期时间
    if file_info["username"] != username and user_info.get("is_admin", 0) != 1:
        return {"status": "error", "message": "permission denied"}

    # 计算新的过期时间
    expiry_map = {
        "1 hour": datetime.now(UTC) + timedelta(hours=1),
        "1 day": datetime.now(UTC) + timedelta(days=1),
        "1 week": datetime.now(UTC) + timedelta(weeks=1),
        "1 month": datetime.now(UTC) + timedelta(days=30),
        "forever": datetime.now(UTC) + timedelta(days=365 * 10),
    }
    new_expiry_date = expiry_map.get(expiry_option, datetime.now(UTC) + timedelta(days=1))

    # 更新文件过期时间
    if db_update_file_expiry(file_hash, new_expiry_date):
        app_logger.info(
            f"File expiry updated: '{file_info['file_name']}', hash: {file_hash}, new expiry: {expiry_option}, by user: {username}, Client-IP: {client_ip}"
        )

        # 返回更新后的信息
        return {
            "status": "success",
            "expiry_date": new_expiry_date.isoformat(),
            "expiry_formatted": new_expiry_date.strftime("%Y-%m-%d %H:%M:%S"),
            "expiry_relative": get_relative_time(new_expiry_date),
        }
    else:
        error_msg = f"Failed to update file expiry: '{file_info['file_name']}', hash: {file_hash}"
        app_logger.warning(error_msg)
        return {"status": "error", "message": "failed to update expiry"}
