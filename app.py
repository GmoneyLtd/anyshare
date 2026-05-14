from config import Config
from web.server import setup_app, start_cleanup_task, start_server


def main() -> None:
    # 加载配置
    config = Config()

    # 配置应用
    app_logger = setup_app(config)

    # 启动定时任务
    start_cleanup_task()

    # 启动服务器
    start_server(config, app_logger)


if __name__ == "__main__":
    main()
