#!/usr/bin/env bash
# 统一管理 funmovie 唯一的长期运行服务：DHT 磁力链接采集。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$RUN_DIR/logs"

# ---- 服务配置 ----
SERVICE_NAME="funmovie-dht"
SERVICE_PORT=9099
SERVICE_CLI="funmovie-dht"
# ------------------

ACTION="${1:-}"
VERSION="${2:-}"

usage() {
  echo "用法: $0 {install-dev|install-prod|upgrade|rollback|publish|start|stop|restart|run|status} [version]" >&2
  exit 1
}

[[ -n "$ACTION" ]] || usage
if [[ "$ACTION" == "rollback" ]]; then
  [[ "$#" -eq 2 ]] || usage
else
  [[ "$#" -eq 1 ]] || {
    echo "错误: ${ACTION} 不接受额外参数" >&2
    usage
  }
fi

pid_file() { printf '%s/%s.pid' "$RUN_DIR" "$SERVICE_NAME"; }
meta_file() { printf '%s/%s.meta' "$RUN_DIR" "$SERVICE_NAME"; }
log_file() { printf '%s/%s-%s.log' "$LOG_DIR" "$SERVICE_NAME" "$(date +%Y-%m-%d)"; }

proc_starttime() {
  local pid="$1"
  if [[ -r "/proc/${pid}/stat" ]]; then
    sed 's/^.*) //' "/proc/${pid}/stat" 2>/dev/null | awk '{print $20}'
  else
    ps -o lstart= -p "$pid" 2>/dev/null | tr -s ' '
  fi
}

proc_cmdline() {
  local pid="$1"
  if [[ -r "/proc/${pid}/cmdline" ]]; then
    tr '\0' ' ' <"/proc/${pid}/cmdline" 2>/dev/null
  else
    ps -o args= -p "$pid" 2>/dev/null
  fi
}

# 输出 missing/invalid/stale/mismatch/running 之一。
service_state() {
  local pid_f="$1" meta_f="$2"
  [[ -f "$pid_f" ]] || { echo missing; return; }
  local pid
  pid="$(tr -d '[:space:]' <"$pid_f")"
  [[ "$pid" =~ ^[1-9][0-9]*$ ]] || { echo invalid; return; }
  kill -0 "$pid" 2>/dev/null || { echo stale; return; }
  [[ -f "$meta_f" ]] || { echo mismatch; return; }

  local recorded_starttime=""
  while IFS='=' read -r key value; do
    [[ "$key" == "starttime" ]] && recorded_starttime="$value"
  done <"$meta_f"
  [[ -n "$recorded_starttime" && "$recorded_starttime" == "$(proc_starttime "$pid")" ]] || { echo mismatch; return; }
  [[ "$(proc_cmdline "$pid")" == *"$SERVICE_CLI"* ]] || { echo mismatch; return; }
  echo running
}

clear_stale() {
  local state="$1" pid_f="$2" meta_f="$3"
  case "$state" in
    stale | invalid)
      echo "提示: 清理 ${state} PID 文件 ${pid_f}" >&2
      rm -f "$pid_f" "$meta_f"
      ;;
    mismatch)
      echo "错误: PID 文件记录的进程身份不匹配，拒绝操作：${pid_f}" >&2
      return 1
      ;;
  esac
}

require_installed_cli() {
  command -v "$SERVICE_CLI" >/dev/null 2>&1 || {
    echo "错误: 未安装 ${SERVICE_CLI}；请先执行 $0 install-dev 或 $0 install-prod" >&2
    return 1
  }
}

install_dev() { python3 -m pip install --editable "$ROOT_DIR"; }
install_prod() { python3 -m pip install "$ROOT_DIR"; }
upgrade() { python3 -m pip install --upgrade funmovie; }
rollback() {
  [[ -n "$VERSION" ]] || { echo "错误: rollback 必须指定版本号" >&2; usage; }
  python3 -m pip install --force-reinstall "funmovie==${VERSION}"
}
publish() {
  python3 -m build "$ROOT_DIR"
  python3 -m twine upload "$ROOT_DIR"/dist/*
}

start() {
  local pid_f meta_f state log_f pid
  pid_f="$(pid_file)"; meta_f="$(meta_file)"; log_f="$(log_file)"
  state="$(service_state "$pid_f" "$meta_f")"
  if [[ "$state" == "running" ]]; then
    echo "错误: ${SERVICE_NAME} 已在运行 (pid $(cat "$pid_f"))" >&2
    return 1
  fi
  clear_stale "$state" "$pid_f" "$meta_f"
  require_installed_cli
  mkdir -p "$RUN_DIR" "$LOG_DIR"
  echo "启动 ${SERVICE_NAME} (port ${SERVICE_PORT}) ..."
  if command -v setsid >/dev/null 2>&1; then
    env FUNMOVIE_DHT_PORT="$SERVICE_PORT" setsid "$SERVICE_CLI" >>"$log_f" 2>&1 </dev/null &
  else
    nohup env FUNMOVIE_DHT_PORT="$SERVICE_PORT" "$SERVICE_CLI" >>"$log_f" 2>&1 </dev/null &
  fi
  pid=$!
  printf '%s\n' "$pid" >"$pid_f"
  printf 'starttime=%s\n' "$(proc_starttime "$pid")" >"$meta_f"
  disown
  echo "${SERVICE_NAME} 已启动 (pid ${pid}, 日志 ${log_f})"
}

stop() {
  local pid_f meta_f state pid
  pid_f="$(pid_file)"; meta_f="$(meta_file)"; state="$(service_state "$pid_f" "$meta_f")"
  case "$state" in
    running)
      pid="$(cat "$pid_f")"
      kill -TERM -- "-${pid}" 2>/dev/null || kill "$pid" 2>/dev/null || true
      rm -f "$pid_f" "$meta_f"
      echo "${SERVICE_NAME} 已停止"
      ;;
    missing) echo "${SERVICE_NAME} 未在运行" ;;
    *) clear_stale "$state" "$pid_f" "$meta_f"; echo "${SERVICE_NAME} 未在运行" ;;
  esac
}

status() {
  local state pid_f meta_f
  pid_f="$(pid_file)"; meta_f="$(meta_file)"; state="$(service_state "$pid_f" "$meta_f")"
  case "$state" in
    running) echo "${SERVICE_NAME}: running (pid $(cat "$pid_f"), port ${SERVICE_PORT})" ;;
    missing) echo "${SERVICE_NAME}: stopped (port ${SERVICE_PORT})" ;;
    stale | invalid) echo "${SERVICE_NAME}: stopped (存在陈旧 PID 文件 ${pid_f})" ;;
    mismatch) echo "${SERVICE_NAME}: unknown (PID 文件身份不匹配：${pid_f})" ;;
  esac
}

case "$ACTION" in
  install-dev) install_dev ;;
  install-prod) install_prod ;;
  upgrade) upgrade ;;
  rollback) rollback ;;
  publish) publish ;;
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  run) require_installed_cli; exec env FUNMOVIE_DHT_PORT="$SERVICE_PORT" "$SERVICE_CLI" ;;
  status) status ;;
  *) echo "错误: 未知动作: ${ACTION}" >&2; usage ;;
esac
