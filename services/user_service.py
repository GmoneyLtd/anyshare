from services.database_service import (
    add_user as db_add_user,
    delete_user as db_delete_user,
    get_all_users as db_get_all_users,
    get_user as db_get_user,
    get_user_files as db_get_user_files,
    update_user_password as db_update_user_password,
)
from services.logger_service import get_logger

app_logger = get_logger()


def authenticate_user(username: str, password: str, client_ip: str) -> dict:
    """
    用户认证

    Args:
        username: 用户名
        password: 密码
        client_ip: 客户端IP

    Returns:
        dict: 包含认证状态和用户信息的字典
    """
    # 验证用户凭据
    user = db_get_user(username, password)
    if user:
        app_logger.info(f"User {username} logged in successfully, Client-IP: {client_ip}")
        return {"status": "success", "user": user}
    else:
        app_logger.warning(f"Failed login attempt with username: {username}, Client-IP: {client_ip}")
        return {"status": "error", "message": "用户名或密码错误"}


def get_user_files(username: str) -> list:
    """
    获取用户文件列表

    Args:
        username: 用户名

    Returns:
        list: 用户文件列表
    """
    return db_get_user_files(username)


def add_user(
    admin_user: dict,
    new_username: str,
    password: str,
    is_admin: int,
    client_ip: str,
) -> dict:
    """
    添加用户

    Args:
        admin_user: 管理员用户信息
        new_username: 新用户名
        password: 密码
        is_admin: 是否为管理员
        client_ip: 客户端IP

    Returns:
        dict: 包含操作状态的字典
    """
    # 检查权限
    if not admin_user or admin_user.get("is_admin", 0) != 1:
        app_logger.warning(f"Non-admin user {admin_user.get('username')} attempted to add user from IP: {client_ip}")
        return {"status": "error", "message": "permission denied"}

    # 添加用户
    if db_add_user(new_username, password, is_admin):
        app_logger.info(f"User {new_username} added by admin {admin_user.get('username')}, Client-IP: {client_ip}")
        return {"status": "success", "message": "User added successfully"}
    else:
        app_logger.warning(
            f"Failed to add user {new_username} by admin {admin_user.get('username')}, Client-IP: {client_ip}"
        )
        return {"status": "error", "message": "Failed to add user"}


def delete_user(admin_user: dict, username_to_delete: str, client_ip: str) -> dict:
    """
    删除用户

    Args:
        admin_user: 管理员用户信息
        username_to_delete: 要删除的用户名
        client_ip: 客户端IP

    Returns:
        dict: 包含操作状态的字典
    """
    # 检查权限
    if not admin_user or admin_user.get("is_admin", 0) != 1:
        app_logger.warning(f"Non-admin user {admin_user.get('username')} attempted to delete user from IP: {client_ip}")
        return {"status": "error", "message": "permission denied"}

    # 检查是否尝试删除管理员账户
    user_to_delete = db_get_user(username_to_delete)
    if user_to_delete and user_to_delete.get("is_admin", 0) == 1:
        app_logger.warning(
            f"Admin {admin_user.get('username')} attempted to delete admin user {username_to_delete}, Client-IP: {client_ip}"
        )
        return {"status": "error", "message": "Cannot delete admin user"}

    # 删除用户
    if db_delete_user(username_to_delete):
        app_logger.info(
            f"User {username_to_delete} deleted by admin {admin_user.get('username')}, Client-IP: {client_ip}"
        )
        return {"status": "success", "message": "User deleted successfully"}
    else:
        app_logger.warning(
            f"Failed to delete user {username_to_delete} by admin {admin_user.get('username')}, Client-IP: {client_ip}"
        )
        return {"status": "error", "message": "Failed to delete user"}


def change_password(
    current_user: dict,
    target_username: str,
    new_password: str,
    client_ip: str,
) -> dict:
    """
    修改密码

    Args:
        current_user: 当前用户信息
        target_username: 目标用户名
        new_password: 新密码
        client_ip: 客户端IP

    Returns:
        dict: 包含操作状态的字典
    """
    if not current_user:
        return {"status": "error", "message": "unauthorized"}

    # 权限检查: 管理员可以修改任意用户密码, 普通用户只能修改自己密码
    if current_user.get("is_admin", 0) != 1 and current_user.get("username") != target_username:
        return {"status": "error", "message": "permission denied"}

    # 更新密码
    if db_update_user_password(target_username, new_password):
        app_logger.info(f"User {target_username} password changed by {current_user.get('username')}")
        return {"status": "success", "message": "password updated"}
    else:
        return {"status": "error", "message": "failed to update password"}


def get_all_users(admin_user: dict, client_ip: str) -> dict:
    """
    获取所有用户列表

    Args:
        admin_user: 管理员用户信息
        client_ip: 客户端IP

    Returns:
        dict: 包含用户列表的字典
    """
    # 检查权限
    if not admin_user or admin_user.get("is_admin", 0) != 1:
        app_logger.warning(
            f"Non-admin user {admin_user.get('username') if admin_user else 'unknown'} attempted to access users list from IP: {client_ip}"
        )
        return {"status": "error", "message": "permission denied"}

    # 获取所有用户
    users = db_get_all_users()
    app_logger.info(
        f"Admin {admin_user.get('username')} accessed users list, total users: {len(users)}, Client-IP: {client_ip}"
    )

    # 返回用户列表
    return {"status": "success", "users": users}
