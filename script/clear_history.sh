#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" != "--yes" ]]; then
  echo "用法: $0 --yes （清空历史并强制推送，默认禁止误触发）" >&2
  exit 1
fi
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "错误: 不是 git 仓库" >&2; exit 1; }
git remote get-url origin >/dev/null 2>&1 || { echo "错误: 未找到远端 origin" >&2; exit 1; }
#1.Checkout
git checkout --orphan latest_branch
#2. Add all the files
git add -A
#3. Commit the changes
git commit -am "维护: 清理提交历史"
#4. Delete the branch
git branch -D master
#5.Rename the current branch to master
git branch -m master
#6.Finally, force update your repository
git push -f origin master
