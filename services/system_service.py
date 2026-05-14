from datetime import UTC, datetime

from services.database_service import get_user_files as db_get_user_files
from services.logger_service import get_logger

app_logger = get_logger()


def get_system_config(anonymous: str, file_limit_size: str, user_limit_size: str) -> dict:
    """
    获取系统配置

    Args:
        anonymous: 是否允许匿名访问
        file_limit_size: 文件大小限制
        user_limit_size: 用户存储限制

    Returns:
        dict: 系统配置信息
    """
    return {
        "status": "success",
        "anonymous": anonymous,
        "file_limit_size": file_limit_size,
        "user_limit_size": user_limit_size,
    }


def update_system_config(
    admin_user: dict,
    anonymous: str | None = None,
    file_limit_size: str | None = None,
    client_ip: str | None = None,
) -> dict:
    """
    更新系统配置

    Args:
        admin_user: 管理员用户信息
        anonymous: 是否允许匿名访问
        file_limit_size: 文件大小限制
        client_ip: 客户端IP

    Returns:
        dict: 包含操作状态的字典
    """
    # 检查权限
    if not admin_user or admin_user.get("is_admin", 0) != 1:
        return {"status": "error", "message": "permission denied"}

    # 更新配置
    app_logger.info(f"System config updated by admin {admin_user.get('username')}")
    return {"status": "success", "message": "config updated"}


def calculate_statistics(username: str) -> dict:
    """
    计算文件统计信息

    Args:
        username: 用户名

    Returns:
        dict: 统计信息
    """
    # 获取所有文件
    files = db_get_user_files(username)
    app_logger.info(f"Admin stats requested, total files: {len(files)}")

    # 计算统计信息
    active_files = len(files)
    total_size = sum(file["file_size"] for file in files)

    # 格式化存储大小
    storage_used = format_size(total_size)

    # 返回统计信息
    return {
        "status": "success",
        "active_files": active_files,
        "storage_used": storage_used,
    }


def format_size(size_bytes: int) -> str:
    """
    格式化文件大小

    Args:
        size_bytes: 字节数

    Returns:
        str: 格式化后的文件大小
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KiB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MiB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GiB"


def get_relative_time(date: datetime) -> str:
    """
    获取相对时间描述

    Args:
        date: 日期时间对象

    Returns:
        str: 相对时间描述
    """
    now = datetime.now(UTC)
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
