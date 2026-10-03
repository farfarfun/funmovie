#!/usr/bin/env bash
# 统一管理 funmovie 唯一的长期运行服务：DHT 磁力链接采集（`funmovie.magnet.core`，
# 内部调用 crawler.start_server()，永久阻塞直到被终止）。
#
# aria2 下载提交（magnet_to_torrent_aria2c）、种子解析（parse_torrent）是各自独立
# 的一次性批处理任务，不是长期运行服务，不归本脚本管理，按 README 里的用法单独运行。
#
# 用法: scripts/setup.sh {start|stop|restart|run} <dev|prod>
#       scripts/setup.sh status [dev|prod]
#   start/run 的环境必须显式指定；status 省略环境时依次报告 dev 和 prod。
#   start   —— 后台运行，PID/日志在 .run/ 下
#   run     —— 前台运行，便于调试
#   stop    —— 停止后台进程（连同 start_server() 派生出的多进程子进程一起终止）
#   status  —— 非交互查询运行状态
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$RUN_DIR" "$LOG_DIR"

MODULE="funmovie.magnet.core"

ACTION="${1:-}"
ENV_NAME="${2:-}"

usage() {
  echo "用法: $0 {start|stop|restart|run} <dev|prod>" >&2
  echo "      $0 status [dev|prod]" >&2
  exit 1
}

[[ -n "$ACTION" ]] || usage
case "$ACTION" in
  start | stop | restart | run | status) ;;
  *)
    echo "错误: 未知动作: ${ACTION}" >&2
    usage
    ;;
esac

if [[ -z "$ENV_NAME" ]]; then
  if [[ "$ACTION" != "status" ]]; then
    echo "错误: ${ACTION} 必须指定环境 dev 或 prod" >&2
    usage
  fi
  ENVS="dev prod"
else
  case "$ENV_NAME" in
    dev | prod) ENVS="$ENV_NAME" ;;
    *)
      echo "错误: 必须指定环境 dev 或 prod" >&2
      usage
      ;;
  esac
fi

# ---- PID / 日志 / 身份文件工具函数（单服务仓库，直接内联，不单独拆 lib/） ----

pid_file() { printf '%s/%s.pid' "$RUN_DIR" "$1"; }
meta_file() { printf '%s/%s.meta' "$RUN_DIR" "$1"; }
log_file() { printf '%s/%s-%s.log' "$LOG_DIR" "$1" "$(date +%Y-%m-%d)"; }

proc_starttime() {
  local pid="$1"
  if [[ -r "/proc/${pid}/stat" ]]; then
    sed 's/^.*) //' "/proc/${pid}/stat" 2>/dev/null | awk '{print $20}'
    return 0
  fi
  ps -o lstart= -p "$pid" 2>/dev/null | tr -s ' '
}

proc_cmdline() {
  local pid="$1"
  if [[ -r "/proc/${pid}/cmdline" ]]; then
    tr '\0' ' ' <"/proc/${pid}/cmdline" 2>/dev/null
    return 0
  fi
  ps -o args= -p "$pid" 2>/dev/null
}

record_process() {
  local pid_f="$1" meta_f="$2" pid="$3" identity="$4"
  printf '%s\n' "$pid" >"$pid_f"
  {
    printf 'identity=%s\n' "$identity"
    printf 'starttime=%s\n' "$(proc_starttime "$pid")"
  } >"$meta_f"
}

# 输出 missing/invalid/stale/mismatch/running 之一
service_state() {
  local pid_f="$1" meta_f="$2" identity="$3"
  [[ -f "$pid_f" ]] || { echo missing; return 0; }

  local pid
  pid="$(tr -d '[:space:]' <"$pid_f")"
  [[ "$pid" =~ ^[1-9][0-9]*$ ]] || { echo invalid; return 0; }
  kill -0 "$pid" 2>/dev/null || { echo stale; return 0; }
  [[ -f "$meta_f" ]] || { echo mismatch; return 0; }

  local recorded_identity="" recorded_starttime=""
  while IFS='=' read -r key value; do
    case "$key" in
      identity) recorded_identity="$value" ;;
      starttime) recorded_starttime="$value" ;;
    esac
  done <"$meta_f"

  local now_starttime
  now_starttime="$(proc_starttime "$pid")"
  if [[ -z "$recorded_starttime" || "$recorded_starttime" != "$now_starttime" ]]; then
    echo mismatch
    return 0
  fi

  local token="${recorded_identity:-$identity}"
  if [[ -n "$token" ]]; then
    local cmdline
    cmdline="$(proc_cmdline "$pid")"
    [[ "$cmdline" == *"$token"* ]] || { echo mismatch; return 0; }
  fi
  echo running
}

clear_stale() {
  local name="$1" state="$2" pid_f="$3" meta_f="$4"
  case "$state" in
    stale)
      echo "提示: ${name} 的 pid 文件是陈旧残留（进程已退出），已清理 ${pid_f}" >&2
      rm -f "$pid_f" "$meta_f"
      ;;
    invalid)
      echo "提示: ${name} 的 pid 文件内容不是合法 PID，已清理 ${pid_f}" >&2
      rm -f "$pid_f" "$meta_f"
      ;;
    mismatch)
      echo "错误: ${name} 的 pid 文件记录的 PID 当前属于另一个进程，拒绝操作" >&2
      echo "      确认无误后手工删除 ${pid_f} 与 ${meta_f} 再重试。" >&2
      return 1
      ;;
  esac
  return 0
}

# prod 下校验 funmovie 是已安装的正式包（非 editable、非源码树）。
# 清空 PYTHONPATH + 用 python3 -I（隔离模式）+ 切到不含 Python 模块的安全目录，
# 三重保证不会误判「能 import」就等于「已安装」。
require_installed_package() {
  mkdir -p "$RUN_DIR"
  if ! (
    cd "$RUN_DIR" || exit 1
    PYTHONPATH="" python3 -I - <<'PYCHECK'
import importlib
import sys
from pathlib import Path

try:
    module = importlib.import_module("funmovie")
except Exception as exc:
    print(f"import funmovie 失败: {exc.__class__.__name__}: {exc}", file=sys.stderr)
    raise SystemExit(1) from None

origin = getattr(module, "__file__", None)
if origin is None:
    print("funmovie 没有 __file__，无法确认安装来源", file=sys.stderr)
    raise SystemExit(1)

resolved = Path(origin).resolve()
if not any(part in ("site-packages", "dist-packages") for part in resolved.parts):
    print(f"funmovie 解析到 {resolved}，不在 site-packages/dist-packages 下", file=sys.stderr)
    print("（典型原因：editable 安装，或直接从源码工作树导入）", file=sys.stderr)
    raise SystemExit(1)
print(resolved)
PYCHECK
  ); then
    echo "错误: prod 要求运行已安装的 funmovie 正式包，当前校验未通过。" >&2
    echo "      请执行 pip install funmovie（不要用 -e）后再启动 prod；" >&2
    echo "      本地源码调试请改用 dev 环境。" >&2
    return 1
  fi
  return 0
}

installed_version() {
  (
    cd "$RUN_DIR" || exit 1
    PYTHONPATH="" python3 -I -c "import importlib.metadata as m; print(m.version('funmovie'))" 2>/dev/null
  ) || echo "unknown"
}

cmd=()
command_for() {
  local env_name="$1"
  if [[ "$env_name" == "prod" ]]; then
    require_installed_package
    cmd=(python3 -m "$MODULE")
  else
    cmd=(env "PYTHONPATH=$ROOT_DIR/src" python3 -m "$MODULE")
  fi
}

run_one() {
  local env_name="$1" sub_action="$2"
  local name="funmovie-dht-${env_name}"
  local pid_f meta_f log_f
  pid_f="$(pid_file "$name")"
  meta_f="$(meta_file "$name")"
  log_f="$(log_file "$name")"
  local identity="$MODULE"

  case "$sub_action" in
    start)
      local state
      state="$(service_state "$pid_f" "$meta_f" "$identity")"
      if [[ "$state" == "running" ]]; then
        echo "${name} 已在运行 (pid $(cat "$pid_f"))"
        return 0
      fi
      clear_stale "$name" "$state" "$pid_f" "$meta_f"

      command_for "$env_name"
      echo "启动 ${name} ..."
      # 用 setsid 起一个新会话：start_server() 会 fork 多个子进程，
      # 必须让它们共享同一个进程组，stop 时才能连同子进程一并杀掉。
      if command -v setsid >/dev/null 2>&1; then
        setsid "${cmd[@]}" >>"$log_f" 2>&1 </dev/null &
      else
        echo "警告: 未找到 setsid，无法保证后台子进程一并被 stop 终止" >&2
        nohup "${cmd[@]}" >>"$log_f" 2>&1 </dev/null &
      fi
      local pid=$!
      record_process "$pid_f" "$meta_f" "$pid" "$identity"
      disown
      echo "${name} 已启动 (pid ${pid}, 日志 ${log_f})"
      ;;
    run)
      command_for "$env_name"
      echo "前台运行 ${name} ..."
      cd "$RUN_DIR"
      exec "${cmd[@]}"
      ;;
    stop)
      local state
      state="$(service_state "$pid_f" "$meta_f" "$identity")"
      case "$state" in
        running)
          local pid
          pid="$(cat "$pid_f")"
          # 负 PID 表示向整个进程组发信号，连 start_server() 派生的子进程一起终止
          kill -TERM -- "-${pid}" 2>/dev/null || kill "$pid" 2>/dev/null || true
          rm -f "$pid_f" "$meta_f"
          echo "${name} 已停止"
          ;;
        missing)
          echo "${name} 未在运行"
          ;;
        *)
          clear_stale "$name" "$state" "$pid_f" "$meta_f"
          echo "${name} 未在运行"
          ;;
      esac
      ;;
    status)
      local state version
      state="$(service_state "$pid_f" "$meta_f" "$identity")"
      version="$(installed_version)"
      case "$state" in
        running) echo "${name}: running (pid $(cat "$pid_f"), funmovie ${version})" ;;
        missing) echo "${name}: stopped (funmovie ${version})" ;;
        stale | invalid) echo "${name}: stopped (存在陈旧 pid 文件 ${pid_f})" ;;
        mismatch) echo "${name}: unknown (pid 文件记录的 PID 已属于其他进程，见 ${pid_f})" ;;
      esac
      ;;
  esac
}

if [[ "$ACTION" == "run" ]]; then
  # run 只支持单个环境，不支持省略
  run_one "$ENVS" run
  exit 0
fi

for env_name in $ENVS; do
  case "$ACTION" in
    start) run_one "$env_name" start ;;
    stop) run_one "$env_name" stop ;;
    restart)
      run_one "$env_name" stop
      run_one "$env_name" start
      ;;
    status) run_one "$env_name" status ;;
  esac
done
