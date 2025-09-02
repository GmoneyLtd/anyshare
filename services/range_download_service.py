import os
import re
from datetime import UTC, datetime

from services.database_service import get_file as db_get_file
from services.database_service import update_downloads as db_update_downloads
from services.logger_service import get_logger

app_logger = get_logger()


def parse_range_header(range_header, file_size):
    """
    解析HTTP Range头

    Args:
        range_header: Range头内容
        file_size: 文件大小

    Returns:
        tuple: (start, end) 或 None
    """
    if not range_header:
        return None

    # 解析 "bytes=start-end" 格式
    match = re.match(r"bytes=(\d*)-(\d*)", range_header)
    if not match:
        return None

    start_str, end_str = match.groups()

    # 处理各种Range格式
    if start_str and end_str:
        # bytes=200-1000
        start = int(start_str)
        end = int(end_str)
    elif start_str and not end_str:
        # bytes=200-
        start = int(start_str)
        end = file_size - 1
    elif not start_str and end_str:
        # bytes=-500 (最后500字节)
        start = file_size - int(end_str)
        end = file_size - 1
    else:
        return None

    # 验证范围
    if start < 0:
        start = 0
    if end >= file_size:
        end = file_size - 1
    if start > end:
        return None

    return (start, end)


def get_file_range_response(file_hash, password, range_header, client_ip, upload_folder):
    """
    处理文件范围下载请求

    Args:
        file_hash: 文件哈希
        password: 文件密码
        range_header: Range头内容
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
            file_path = os.path.join(upload_folder, file_hash)
            if not os.path.exists(file_path):
                return {"status": "error", "message": "File not found on disk"}

            file_size = os.path.getsize(file_path)

            # 解析Range头
            range_info = parse_range_header(range_header, file_size)

            if range_info:
                start, end = range_info
                content_length = end - start + 1

                app_logger.info(
                    f"Range download started: '{file_info['file_name']}', hash: {file_hash}, range: {start}-{end}/{file_size}, Client-IP: {client_ip}"
                )

                # 只在完整下载时更新下载次数
                if start == 0 and end == file_size - 1:
                    db_update_downloads(file_hash)

                return {
                    "status": "partial_content",
                    "file_path": file_path,
                    "file_name": file_info["file_name"],
                    "file_size": file_size,
                    "start": start,
                    "end": end,
                    "content_length": content_length,
                }
            else:
                # 完整文件下载
                app_logger.info(
                    f"Full download started: '{file_info['file_name']}', hash: {file_hash}, Client-IP: {client_ip}"
                )
                db_update_downloads(file_hash)

                return {
                    "status": "success",
                    "file_path": file_path,
                    "file_name": file_info["file_name"],
                    "file_size": file_size,
                }
        else:
            app_logger.warning(f"Incorrect password provided for file: {file_hash}, Client-IP: {client_ip}")
            return {"status": "error", "message": "password error"}

    return {"status": "password_required", "file_hash": file_hash}


def create_range_response_headers(file_size, start, end, file_name):
    """
    创建范围下载响应头

    Args:
        file_size: 文件大小
        start: 开始位置
        end: 结束位置
        file_name: 文件名

    Returns:
        dict: 响应头字典
    """
    content_length = end - start + 1

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": "application/octet-stream",
        "Content-Disposition": f'attachment; filename="{file_name}"',
    }

    return headers


def read_file_range(file_path, start, end):
    """
    读取文件指定范围的内容

    Args:
        file_path: 文件路径
        start: 开始位置
        end: 结束位置

    Returns:
        generator: 文件内容生成器
    """
    chunk_size = 8192  # 8KB chunks

    with open(file_path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1

        while remaining > 0:
            read_size = min(chunk_size, remaining)
            chunk = f.read(read_size)
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def get_content_type(file_name):
    """
    根据文件名获取Content-Type

    Args:
        file_name: 文件名

    Returns:
        str: Content-Type
    """
    ext = os.path.splitext(file_name)[1].lower()

    content_types = {
        ".txt": "text/plain",
        ".html": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".json": "application/json",
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".mp4": "video/mp4",
        ".mp3": "audio/mpeg",
        ".zip": "application/zip",
        ".rar": "application/x-rar-compressed",
        ".7z": "application/x-7z-compressed",
    }

    return content_types.get(ext, "application/octet-stream")


def validate_range_request(range_header, file_size):
    """
    验证Range请求是否有效

    Args:
        range_header: Range头内容
        file_size: 文件大小

    Returns:
        bool: 是否有效
    """
    if not range_header:
        return True  # 没有Range头是有效的完整请求

    range_info = parse_range_header(range_header, file_size)
    return range_info is not None
