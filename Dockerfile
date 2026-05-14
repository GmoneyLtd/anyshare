# -------------- 构建阶段 --------------
FROM ghcr.io/astral-sh/uv:python3.13-alpine AS builder
# 设置工作目录为 app
WORKDIR /app
# 复制项目依赖文件
COPY pyproject.toml uv.lock ./
# 创建虚拟环境并安装依赖
RUN uv sync --frozen --no-cache
# 复制项目代码
COPY . .

# -------------- 运行阶段 --------------
FROM python:3.13.7-alpine
# 使用 apk 安装 curl
RUN apk add --no-cache curl
WORKDIR /app
# 复制应用代码
COPY --from=builder /app /app
# 创建相关文件夹并保证权限属于 appuser
RUN addgroup -S -g 1000 appuser && adduser -S -u 1000 appuser -G appuser && \
    mkdir -p /app/log /app/upload /app/upload/temp && \
    chown -R appuser:appuser /app
USER appuser
# 设置环境变量，使用 `.venv` 作为虚拟环境及服务相关配置
ENV PATH="/app/.venv/bin:$PATH"
ENV ADMIN_USERNAME=admin
ENV ADMIN_PASSWORD=123456
ENV LOG_LEVEL=DEBUG
ENV ANONYMOUS=false


# 暴露应用端口
EXPOSE 8000
# 应用程序健康检查
HEALTHCHECK --interval=60s --timeout=5s --start-period=20s  --retries=3 CMD [ "curl", "-f", "http://localhost:8000/api/healthz" ]

# 启动命令
CMD ["python", "app.py"]