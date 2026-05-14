import os
import secrets


class Config:
    # 应用配置
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    THREADS = int(os.getenv("THREADS", 4))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")

    # 路径配置
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "./upload")
    LOG_FOLDER = os.getenv("LOG_FOLDER", "./log")

    # 功能配置
    ANONYMOUS = os.getenv("ANONYMOUS", "true")
    FILE_LIMIT_SIZE = os.getenv("FILE_LIMIT_SIZE", "10.00")
    USER_LIMIT_SIZE = os.getenv("USER_LIMIT_SIZE", "2.00")

    # 数据库配置
    DB_NAME = os.getenv("DB_NAME", "anyshare.db")

    # 管理员配置
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

    # Cookie Secret
    COOKIE_SECRET = os.getenv("COOKIE_SECRET", secrets.token_hex(16))
