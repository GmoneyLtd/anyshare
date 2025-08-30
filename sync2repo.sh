#!/bin/bash

# anyshare 仓库同步脚本
# 本脚本用于设置双仓库同步并将 multi-user 设为默认分支
# 作者: GmoneyLtd Team
# 版本: 2.1.1
# 功能: 配置Git双远程仓库推送，支持同时推送到多个代码托管平台

echo "============= 🚀 开始 anyShare 仓库同步设置 ============="

# ============================================================================
# 用户选择：双仓库推送方式
# ============================================================================
echo ""
echo "📋 请选择双仓库推送方式:"
echo "1. 使用独立远程仓库 (origin + backup) - 分别管理，灵活控制"
echo "2. 使用统一远程仓库 (all) - 一次推送到多个仓库，简化操作"
echo ""
echo "方式说明:"
echo "   方式1: 创建 origin 和 backup 两个独立的远程仓库"
echo "        - 优点: 可以单独推送到某个仓库，控制更精确"
echo "        - 缺点: 需要执行两次推送命令"
echo ""
echo "   方式2: 创建一个 'all' 特殊远程仓库"
echo "        - 优点: 一次命令推送到所有仓库，操作简单"
echo "        - 缺点: 无法单独控制某个仓库的推送"
echo ""

# 获取用户选择
while true; do
    read -p "请输入您的选择 (1 或 2): " PUSH_METHOD
    case $PUSH_METHOD in
        1)
            echo "✅ 已选择: 使用独立远程仓库方式 (origin + backup)"
            USE_SEPARATE_REMOTES=true
            break
            ;;
        2)
            echo "✅ 已选择: 使用统一远程仓库方式 (all)"
            USE_SEPARATE_REMOTES=false
            break
            ;;
        *)
            echo "❌ 无效选择，请输入 1 或 2"
            ;;
    esac
done

echo ""

# ============================================================================
# 第一步：创建并切换到 multi-user 分支
# ============================================================================
# 检查 multi-user 分支是否存在，如果存在则切换，如果不存在则创建
echo "📋 设置 multi-user 分支..."
if git show-ref --verify --quiet refs/heads/multi-user; then
    # 分支已存在，直接切换
    echo "📋 分支 multi-user 已存在，正在切换到该分支..."
    git switch multi-user
else
    # 分支不存在，创建新分支
    echo "📋 创建新分支 multi-user..."
    git checkout -b multi-user
fi

# ============================================================================
# 第二步：查看当前远程仓库配置
# ============================================================================
# 显示当前所有已配置的远程仓库信息，包括名称和URL
echo "📋 当前 Git 远程仓库配置:"
git remote -v

# ============================================================================
# 第三步：配置远程仓库 URL
# ============================================================================
# 定义两个远程仓库的 URL 地址
# FIRST_REPO_URL: 主要仓库（GitHub 公共仓库）
# SECOND_REPO_URL: 备份仓库（自建 Gitea 服务器）
# 注意：根据实际情况修改这些 URL
FIRST_REPO_URL="https://github.com/GmoneyLtd/anyshare.git"
SECOND_REPO_URL="https://gitea.apuer.tech/GmoneyLtd/anyshare.git"

echo "📋 配置的仓库地址:"
echo "   主仓库: $FIRST_REPO_URL"
echo "   备份仓库: $SECOND_REPO_URL"

# ============================================================================
# 第四步：配置远程仓库（根据用户选择的方式）
# ============================================================================
echo "📋 配置远程仓库..."

# 4.1: 首先确保 origin 远程仓库存在并配置正确的 URL
echo "📋 设置主远程仓库 (origin)..."
ORIGIN_URL=$(git remote get-url origin 2>/dev/null)
if [ -n "$ORIGIN_URL" ]; then
    # origin 远程仓库已存在
    echo "📋 当前 origin 远程仓库 URL: $ORIGIN_URL"
else
    # origin 远程仓库不存在，需要添加
    echo "📋 添加 origin 远程仓库..."
    git remote add origin "$FIRST_REPO_URL"
    echo "✅ 已添加 origin 远程仓库: origin -> $FIRST_REPO_URL"
fi

echo ""

# 4.2: 根据用户选择配置备份远程仓库或统一远程仓库
if [ "$USE_SEPARATE_REMOTES" = true ]; then
    # 方式1: 配置独立的 backup 远程仓库
    echo "📋 设置备份远程仓库 (backup)..."
    if ! git remote | grep -q "^backup$"; then
        git remote add backup "$SECOND_REPO_URL"
        echo "✅ 已成功添加备份远程仓库: backup -> $SECOND_REPO_URL"
    else
        echo "📋 备份远程仓库已存在，跳过添加步骤"
    fi
else
    # 方式2: 配置统一的 'all' 远程仓库
    echo "📋 设置统一远程仓库 (all)..."
    if ! git remote | grep -q "^all$"; then
        echo "📋 创建 'all' 远程仓库用于双重推送..."
        
        # 第一步：添加 'all' 远程仓库（设置 fetch 和初始 push URL）
        # Fetch URL: FIRST_REPO_URL
        # Push URL: FIRST_REPO_URL
        git remote add all "$FIRST_REPO_URL"
        
        # 第二步：启用多推送模式并确保第一个仓库在推送列表中
        # 注意：这一步会覆盖默认的Push URL
        # Fetch URL: FIRST_REPO_URL
        # Push URL: FIRST_REPO_URL
        git remote set-url --add --push all "$FIRST_REPO_URL"
        
        # 第三步：为 'all' 远程仓库添加第二个Push URL
        # 现在 'all' 远程仓库将同时推送到两个 URL
        # Fetch URL: FIRST_REPO_URL
        # Push URL: FIRST_REPO_URL SECOND_REPO_URL
        git remote set-url --add --push all "$SECOND_REPO_URL"
        
        echo "✅ 已成功配置 'all' 远程仓库，支持同时推送到两个仓库"
    else
        echo "📋 'all' 远程仓库已存在，跳过配置步骤"
    fi
fi

echo ""
echo "📋 当前远程仓库配置:"
git remote -v

# ============================================================================
# 第五步：暂存并提交当前更改
# ============================================================================
echo "📋 暂存并提交当前更改..."

# 将所有更改添加到暂存区
git add .

# 检查是否有需要提交的更改
# git diff --staged --quiet 命令在有暂存更改时返回非零退出码
if git diff --staged --quiet; then
    # 没有更改需要提交
    echo "📋 没有更改需要提交"
else
    # 有更改需要提交，执行提交操作
    echo "📋 正在提交更改..."
    git commit -m "feat: setup dual repository sync and multi-user branch

- Configure repository for dual remote synchronization
- Set multi-user as default development branch
- Add sync script for automated deployment"
    echo "✅ 已成功提交更改"
fi

# ============================================================================
# 第六步：推送所有分支和标签到各个远程仓库（根据用户选择的方式）
# ============================================================================
echo "📋 开始推送所有分支和标签到远程仓库..."

if [ "$USE_SEPARATE_REMOTES" = true ]; then
    # 方式1：使用独立远程仓库 (origin + backup)
    echo "📋 使用独立远程仓库方式进行推送..."
    
    # 推送到 origin 远程仓库（所有分支和标签）
    if git remote | grep -q "^origin$"; then
        echo "📋 推送所有分支和标签到 origin 远程仓库..."
        
        # 推送所有分支
        if git push origin --all 2>/dev/null; then
            echo "✅ 成功推送所有分支到 origin"
        else
            echo "⚠️  推送分支到 origin 失败（首次设置时这是正常的）"
            echo "   可能的原因：认证失败、网络问题或远程仓库不存在"
        fi
        
        # 推送所有标签（强制推送）
        if git push origin --tags --force 2>/dev/null; then
            echo "✅ 成功强制推送所有标签到 origin"
        else
            echo "⚠️  强制推送标签到 origin 失败（可能没有标签或认证问题）"
        fi
    else
        echo "⚠️  origin 远程仓库不存在，跳过推送"
    fi
    
    echo ""
    
    # 推送到 backup 远程仓库（所有分支和标签）
    if git remote | grep -q "^backup$"; then
        echo "📋 推送所有分支和标签到 backup 远程仓库..."
        
        # 推送所有分支
        if git push backup --all 2>/dev/null; then
            echo "✅ 成功推送所有分支到 backup"
        else
            echo "⚠️  推送分支到 backup 失败（首次设置时这是正常的）"
            echo "   可能的原因：认证失败、网络问题或远程仓库不存在"
        fi
        
        # 推送所有标签（强制推送）
        if git push backup --tags --force 2>/dev/null; then
            echo "✅ 成功强制推送所有标签到 backup"
        else
            echo "⚠️  强制推送标签到 backup 失败（可能没有标签或认证问题）"
        fi
    else
        echo "⚠️  backup 远程仓库不存在，跳过推送"
    fi
    
    echo ""
    echo "📊 独立远程仓库推送完成"
    echo "   - 主仓库 (origin): $FIRST_REPO_URL"
    echo "   - 备份仓库 (backup): $SECOND_REPO_URL"
    
else
    # 方式2：使用统一远程仓库 ('all')
    echo "📋 使用统一远程仓库方式进行推送..."
    
    # 推送到 all 远程仓库（双重推送 - 所有分支和标签）
    # 这是最重要的推送操作，将同时推送所有分支和标签到两个仓库
    if git remote | grep -q "^all$"; then
        echo "📋 同时推送所有分支和标签到所有远程仓库..."
        
        # 获取 'all' 远程仓库的所有推送 URL
        PUSH_URLS=$(git remote get-url --push --all all 2>/dev/null)
        
        if [ -n "$PUSH_URLS" ]; then
            echo "📋 将推送到以下仓库:"
            echo "$PUSH_URLS" | while read -r url; do
                echo "   - $url"
            done
            echo ""
            
            # 推送所有分支
            echo "📋 推送所有分支..."
            PUSH_BRANCHES_OUTPUT=$(git push all --all 2>&1)
            PUSH_BRANCHES_RESULT=$?
            
            # 推送所有标签（强制推送）
            echo "📋 强制推送所有标签..."
            PUSH_TAGS_OUTPUT=$(git push all --tags --force 2>&1)
            PUSH_TAGS_RESULT=$?
            
            # 分析推送结果
            echo ""
            echo "📊 推送结果汇总:"
            
            # 分析分支推送结果
            if [ $PUSH_BRANCHES_RESULT -eq 0 ]; then
                echo "✅ 所有分支推送成功"
                
                # 显示推送的分支信息
                LOCAL_BRANCHES=$(git branch --format="%(refname:short)" | tr '\n' ' ')
                echo "   📋 已推送的分支: $LOCAL_BRANCHES"
                
                # 分析各个仓库的分支推送结果
                if echo "$PUSH_BRANCHES_OUTPUT" | grep -q "$FIRST_REPO_URL"; then
                    echo "   ✅ 主仓库分支推送成功: $FIRST_REPO_URL"
                fi
                if echo "$PUSH_BRANCHES_OUTPUT" | grep -q "$SECOND_REPO_URL"; then
                    echo "   ✅ 备份仓库分支推送成功: $SECOND_REPO_URL"
                fi
            else
                echo "⚠️  部分或全部分支推送失败"
                
                # 分析分支推送错误
                if echo "$PUSH_BRANCHES_OUTPUT" | grep -qi "error.*$FIRST_REPO_URL\|fatal.*$FIRST_REPO_URL"; then
                    echo "   ❌ 主仓库分支推送失败: $FIRST_REPO_URL"
                else
                    echo "   ✅ 主仓库分支推送成功: $FIRST_REPO_URL"
                fi
                
                if echo "$PUSH_BRANCHES_OUTPUT" | grep -qi "error.*$SECOND_REPO_URL\|fatal.*$SECOND_REPO_URL"; then
                    echo "   ❌ 备份仓库分支推送失败: $SECOND_REPO_URL"
                else
                    echo "   ✅ 备份仓库分支推送成功: $SECOND_REPO_URL"
                fi
            fi
            
            echo ""
            
            # 分析标签推送结果
            if [ $PUSH_TAGS_RESULT -eq 0 ]; then
                echo "✅ 所有标签推送成功"
                
                # 显示推送的标签信息
                LOCAL_TAGS=$(git tag -l | tr '\n' ' ')
                if [ -n "$LOCAL_TAGS" ]; then
                    echo "   🏷️  已推送的标签: $LOCAL_TAGS"
                else
                    echo "   📋 当前没有标签需要推送"
                fi
                
                # 分析各个仓库的标签推送结果
                if echo "$PUSH_TAGS_OUTPUT" | grep -q "$FIRST_REPO_URL"; then
                    echo "   ✅ 主仓库标签推送成功: $FIRST_REPO_URL"
                fi
                if echo "$PUSH_TAGS_OUTPUT" | grep -q "$SECOND_REPO_URL"; then
                    echo "   ✅ 备份仓库标签推送成功: $SECOND_REPO_URL"
                fi
            else
                echo "⚠️  部分或全部标签推送失败"
                
                # 分析标签推送错误
                if echo "$PUSH_TAGS_OUTPUT" | grep -qi "error.*$FIRST_REPO_URL\|fatal.*$FIRST_REPO_URL"; then
                    echo "   ❌ 主仓库标签推送失败: $FIRST_REPO_URL"
                else
                    echo "   ✅ 主仓库标签推送成功: $FIRST_REPO_URL"
                fi
                
                if echo "$PUSH_TAGS_OUTPUT" | grep -qi "error.*$SECOND_REPO_URL\|fatal.*$SECOND_REPO_URL"; then
                    echo "   ❌ 备份仓库标签推送失败: $SECOND_REPO_URL"
                else
                    echo "   ✅ 备份仓库标签推送成功: $SECOND_REPO_URL"
                fi
            fi
            
            # 如果有任何推送失败，显示详细错误信息
            if [ $PUSH_BRANCHES_RESULT -ne 0 ] || [ $PUSH_TAGS_RESULT -ne 0 ]; then
                echo ""
                echo "🔍 故障排除信息:"
                echo "   可能的原因:"
                echo "   - 认证失败（检查用户名密码或SSH密钥）"
                echo "   - 网络连接问题"
                echo "   - 远程仓库不存在或没有推送权限"
                echo "   - 分支保护规则阻止推送"
                echo "   - 标签已存在且受保护"
                echo ""
                
                if [ $PUSH_BRANCHES_RESULT -ne 0 ]; then
                    echo "   分支推送详细错误信息:"
                    echo "$PUSH_BRANCHES_OUTPUT" | sed 's/^/   /'
                    echo ""
                fi
                
                if [ $PUSH_TAGS_RESULT -ne 0 ]; then
                    echo "   标签推送详细错误信息:"
                    echo "$PUSH_TAGS_OUTPUT" | sed 's/^/   /'
                fi
            fi
            
            echo ""
            echo "📋 推送操作完成摘要:"
            if [ $PUSH_BRANCHES_RESULT -eq 0 ] && [ $PUSH_TAGS_RESULT -eq 0 ]; then
                echo "   🎉 所有分支和标签推送成功！"
                echo "   📦 数据已完全同步到主仓库和备份仓库"
            elif [ $PUSH_BRANCHES_RESULT -eq 0 ]; then
                echo "   ✅ 分支推送成功，⚠️ 标签推送部分失败"
            elif [ $PUSH_TAGS_RESULT -eq 0 ]; then
                echo "   ⚠️ 分支推送部分失败，✅ 标签推送成功"
            else
                echo "   ❌ 分支和标签推送均有失败"
            fi
            
        else
            echo "⚠️  无法获取 'all' 远程仓库的推送 URL"
        fi
    else
        echo "⚠️  'all' 远程仓库不存在，无法执行双重推送"
    fi
fi

# ============================================================================
# 第七步：设置本地默认分支
# ============================================================================
# 将本地仓库的默认分支设置为 multi-user
# 这意味着在克隆或初始化时将默认使用这个分支
echo "📋 设置 multi-user 为本地默认分支..."
git symbolic-ref HEAD refs/heads/multi-user
echo "  ✅ 已将 multi-user 设置为本地默认分支"

# ============================================================================
# 脚本执行完成，显示配置摘要和后续步骤
# ============================================================================
echo ""
echo "✅ 仓库同步设置完成！"
echo ""
echo "📋 配置摘要:"
echo "   - 默认分支: multi-user"
echo "   - 当前分支: $(git branch --show-current)"
echo "   - 可用的远程仓库:"
git remote -v
echo ""
echo "🔧 后续步骤:"
echo "1. 在远程仓库平台上设置 multi-user 为默认分支:"
echo "   - GitHub: 仓库设置 → 常规 → 默认分支"
echo "   - GitLab/Gitea: 仓库设置 → 仓库 → 默认分支"
echo "2. 更新任何 CI/CD 配置以使用 multi-user 分支"
echo "3. 通知团队成员关于分支变更"
echo ""
echo "💡 已配置的仓库:"
echo "   - 主仓库: $FIRST_REPO_URL"
echo "   - 备份仓库: $SECOND_REPO_URL"
echo ""
echo "💡 日常使用提示:"
if [ "$USE_SEPARATE_REMOTES" = true ]; then
    echo "   📋 使用独立远程仓库方式的推送命令:"
    echo "   - 推送所有分支到主仓库: git push origin --all"
    echo "   - 推送所有标签到主仓库: git push origin --tags --force"
    echo "   - 推送所有分支到备份仓库: git push backup --all"
    echo "   - 推送所有标签到备份仓库: git push backup --tags --force"
    echo "   - 推送当前分支到主仓库: git push origin"
    echo "   - 推送当前分支到备份仓库: git push backup"
    echo "   - 推送特定分支到主仓库: git push origin <branch-name>"
    echo "   - 推送特定分支到备份仓库: git push backup <branch-name>"
    echo "   - 创建并推送新标签到主仓库: git tag <tag-name> && git push origin --tags --force"
    echo "   - 创建并推送新标签到备份仓库: git tag <tag-name> && git push backup --tags --force"
    echo "   - 同时推送到两个仓库: git push origin --all && git push origin --tags --force && git push backup --all && git push backup --tags --force"
else
    echo "   📋 使用统一远程仓库方式的推送命令:"
    echo "   - 推送所有分支和标签到两个仓库: git push all --all && git push all --tags --force"
    echo "   - 推送当前分支到两个仓库: git push all"
    echo "   - 推送特定分支到两个仓库: git push all <branch-name>"
    echo "   - 推送特定标签到两个仓库: git push all <tag-name> --force"
    echo "   - 创建并推送新标签: git tag <tag-name> && git push all --tags --force"
    echo "   - 只推送到主仓库: git push origin --all && git push origin --tags --force"
    echo "   - 只推送到备份仓库: git push backup --all && git push backup --tags --force (备注：backup 远程需要手动添加)"
fi
echo ""
echo "📚 更多信息:"
echo "   - 查看远程仓库配置: git remote -v"
echo "   - 查看分支状态: git branch -a"
echo "   - 查看推送配置: git remote show all"