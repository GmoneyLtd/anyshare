import os
import threading
import time

from waitress import serve

from services.database_service import delete_expired_files, init_db
from services.logger_service import get_logger, setup_logger
from web.routes import app


def setup_app(config_obj):
    """配置应用"""
    # 创建上传文件夹
    if not os.path.exists(config_obj.UPLOAD_FOLDER):
        os.makedirs(config_obj.UPLOAD_FOLDER)

    # 初始化数据库
    init_db()

    # 初始化日志器
    setup_logger(config_obj.LOG_FOLDER, config_obj.LOG_LEVEL)
    app_logger = get_logger()

    return app_logger


def start_cleanup_task():
    """启动定时清理任务"""

    def run_cleanup_task():
        while True:
            delete_expired_files()
            time.sleep(24 * 60 * 60)  # 每天执行一次

    cleanup_thread = threading.Thread(target=run_cleanup_task, daemon=True)
    cleanup_thread.start()


def start_server(config_obj, app_logger):
    """启动Web服务器"""
    app_logger.info("Starting server...")
    # 启动服务器
    trusted_proxy_headers = ["X-Forwarded-For", "X-Forwarded-Proto", "X-Forwarded-Host", "X-Forwarded-Port"]
    serve(
        app,
        host=config_obj.HOST,
        port=config_obj.PORT,
        channel_timeout=300,  # 增加到300秒(5分钟)以支持大文件下载
        ident="[AnyShare]",
        threads=config_obj.THREADS,
        trusted_proxy="*",
        trusted_proxy_count=5,
        trusted_proxy_headers=trusted_proxy_headers,
    )
