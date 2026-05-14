import os
import sys

from loguru import logger


def setup_logger(log_folder: str, log_level: str = "INFO") -> None:
    """
    配置日志器

    Args:
        log_folder: 日志文件存储目录
        log_level: 日志级别
    """
    # 确保日志目录存在
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)

    # 移除默认的日志处理器
    logger.remove()

    # 添加控制台输出
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <7}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
        colorize=True,
    )

    # 添加文件输出, 每天轮转
    logger.add(
        os.path.join(log_folder, "anyshare_{time:YYYY-MM-DD}_.log"),
        rotation="00:00",
        retention="7 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <7} | {name}:{function}:{line} | {message}",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )


def get_logger() -> type:
    """
    获取日志器实例

    Returns:
        logger: loguru logger 实例
    """
    return logger
