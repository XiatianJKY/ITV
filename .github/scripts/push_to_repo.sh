#!/bin/bash
# .github/scripts/push_to_repo.sh

set -e

echo "📦 检查 Git 状态..."
git status

# 配置 Git
git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

# 获取最新远程更改
echo "🔄 拉取最新远程更改..."
git fetch origin main
git pull origin main --rebase || echo "拉取失败，继续..."

# 检查是否有更改需要提交
if [[ -n $(git status --porcelain) ]]; then
    echo "📝 检测到更改，准备提交..."
    git add output/ data/ || true
    git add *.m3u *.txt 2>/dev/null || true
    git add -A
    
    # 检查是否有实际更改
    if [[ -n $(git status --porcelain) ]]; then
        git commit -m "自动更新 IPTV 列表 - $(date '+%Y-%m-%d %H:%M:%S')"
        
        # 再次拉取并尝试推送
        echo "🚀 推送到远程仓库..."
        git pull origin main --rebase || true
        git push origin main || {
            echo "⚠️ 推送失败，尝试使用 force push with lease..."
            git push --force-with-lease origin main
        }
        echo "✅ 推送成功"
    else
        echo "✅ 无实际更改需要提交"
    fi
else
    echo "✅ 无更改需要提交"
fi
