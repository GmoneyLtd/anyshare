#!/bin/bash

# HWatch Docker 构建和推送脚本
# 功能: 构建多平台Docker镜像并推送到远程仓库
# 支持: 版本标签管理、镜像推送、错误处理
set -e

# 配置参数
REGISTRY="registry.cn-hangzhou.aliyuncs.com"
NAMESPACE="gmoneyltd"
IMAGE_NAME="anyshare"
VERSION="0.1.1"
PLATFORMS="linux/amd64,linux/arm64"

# 构建完整的镜像标签
IMAGE_BASE="${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}"
VERSION_TAG="${IMAGE_BASE}:${VERSION}"
LATEST_TAG="${IMAGE_BASE}:latest"

echo "======== 🚀 开始 anyShare Docker 镜像构建和推送流程 ========"
echo ""
echo "📋 构建配置:"
echo "   仓库地址: ${REGISTRY}"
echo "   命名空间: ${NAMESPACE}"
echo "   镜像名称: ${IMAGE_NAME}"
echo "   版本标签: ${VERSION}"
echo "   支持平台: ${PLATFORMS}"
echo "   版本镜像: ${VERSION_TAG}"
echo "   最新镜像: ${LATEST_TAG}"
echo ""

# 检查Docker环境
echo "🔍 检查Docker环境..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装或不在PATH中"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker 服务未运行"
    exit 1
fi

echo "✅ Docker 环境检查通过"
echo ""

# 检查buildx支持
echo "🔍 检查Docker buildx支持..."
if ! docker buildx version &> /dev/null; then
    echo "❌ Docker buildx 不可用"
    exit 1
fi

echo "✅ Docker buildx 可用"
echo ""

# 检查是否已存在相同版本的镜像标签
echo "🔍 检查远程仓库中的现有标签..."
echo "📋 检查版本标签: ${VERSION_TAG}"

# 尝试拉取现有的版本标签以检查是否存在
if docker pull "${VERSION_TAG}" 2>/dev/null; then
    echo "⚠️  警告: 版本标签 ${VERSION} 已存在于远程仓库"
    echo ""
    echo "请选择处理方式:"
    echo "1. 覆盖现有标签 (强制推送)"
    echo "2. 取消构建"
    echo "3. 使用新的版本号"
    echo ""
    
    while true; do
        read -p "请输入您的选择 (1/2/3): " CHOICE
        case $CHOICE in
            1)
                echo "✅ 选择覆盖现有标签"
                FORCE_PUSH=true
                break
                ;;
            2)
                echo "❌ 取消构建"
                exit 0
                ;;
            3)
                echo "📝 请输入新的版本号 (当前: ${VERSION}):"
                read -p "新版本号: " NEW_VERSION
                if [ -n "$NEW_VERSION" ] && [ "$NEW_VERSION" != "$VERSION" ]; then
                    VERSION="$NEW_VERSION"
                    VERSION_TAG="${IMAGE_BASE}:${VERSION}"
                    echo "✅ 使用新版本号: ${VERSION}"
                    echo "📋 新版本镜像: ${VERSION_TAG}"
                    break
                else
                    echo "❌ 无效的版本号，请重新输入"
                fi
                ;;
            *)
                echo "❌ 无效选择，请输入 1、2 或 3"
                ;;
        esac
    done
else
    echo "✅ 版本标签 ${VERSION} 不存在，可以安全构建"
    FORCE_PUSH=false
fi

echo ""

# 创建或使用buildx构建器
echo "🔧 设置Docker buildx构建器..."
BUILDER_NAME="hwatch-builder"

if ! docker buildx inspect "$BUILDER_NAME" &> /dev/null; then
    echo "📋 创建新的buildx构建器: $BUILDER_NAME"
    docker buildx create --name "$BUILDER_NAME" --use
else
    echo "📋 使用现有的buildx构建器: $BUILDER_NAME"
    docker buildx use "$BUILDER_NAME"
fi

echo "✅ buildx构建器设置完成"
echo ""

# 构建多平台镜像
echo "🔨 开始构建多平台Docker镜像..."
echo "📋 构建平台: ${PLATFORMS}"
echo "📋 镜像标签: ${VERSION_TAG}, ${LATEST_TAG}"
echo ""

BUILD_START_TIME=$(date +%s)

# 执行构建命令
if docker buildx build \
    --no-cache \
    --platform "${PLATFORMS}" \
    -t "${VERSION_TAG}" \
    -t "${LATEST_TAG}" \
    --push \
    . ; then
    
    BUILD_END_TIME=$(date +%s)
    BUILD_DURATION=$((BUILD_END_TIME - BUILD_START_TIME))
    
    echo ""
    echo "✅ Docker 镜像构建并推送成功!"
    echo "📊 构建统计:"
    echo "   构建时长: ${BUILD_DURATION} 秒"
    echo "   构建平台: ${PLATFORMS}"
    echo "   推送标签:"
    echo "     - ${VERSION_TAG}"
    echo "     - ${LATEST_TAG}"
    
else
    echo ""
    echo "❌ Docker 镜像构建失败"
    echo "🔍 故障排除建议:"
    echo "   1. 检查Dockerfile语法"
    echo "   2. 确认网络连接正常"
    echo "   3. 验证仓库访问权限"
    echo "   4. 检查构建上下文中的文件"
    exit 1
fi

echo ""

# 验证推送结果
echo "🔍 验证镜像推送结果..."
echo "📋 验证镜像标签可用性..."

# 验证版本标签
if docker pull "${VERSION_TAG}" &> /dev/null; then
    echo "✅ 版本标签推送成功: ${VERSION_TAG}"
else
    echo "⚠️  版本标签验证失败: ${VERSION_TAG}"
fi

# 验证latest标签
if docker pull "${LATEST_TAG}" &> /dev/null; then
    echo "✅ Latest标签推送成功: ${LATEST_TAG}"
else
    echo "⚠️  Latest标签验证失败: ${LATEST_TAG}"
fi

echo ""

# 清理本地镜像（可选）
echo "🧹 清理本地构建缓存..."
echo "📋 是否清理本地Docker构建缓存? (y/N)"
read -p "选择: " CLEAN_CACHE

if [[ "$CLEAN_CACHE" =~ ^[Yy]$ ]]; then
    echo "🧹 清理Docker构建缓存..."
    docker buildx prune -f
    echo "✅ 构建缓存清理完成"
else
    echo "📋 保留构建缓存"
fi

echo ""
echo "🎉 HWatch Docker 镜像构建和推送流程完成!"
echo ""
echo "📋 使用指南:"
echo "   拉取最新版本: docker pull ${LATEST_TAG}"
echo "   拉取指定版本: docker pull ${VERSION_TAG}"
echo "   运行容器: docker run -d -p 8000:8000 ${LATEST_TAG}"
echo ""
echo "💡 后续步骤:"
echo "   1. 在目标环境中拉取并测试镜像"
echo "   2. 更新部署配置文件中的镜像标签"
echo "   3. 执行滚动更新或重新部署"
echo "   4. 验证应用程序功能正常"
echo ""
