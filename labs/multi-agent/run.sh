#!/usr/bin/env bash
# 启动两个专家(A2A),跑一次 Supervisor,然后停掉。
set -euo pipefail
cd "$(dirname "$0")"

LIVE=0
REGION="${LAB_REGION:-cn-northwest-1}"
QUESTION="查宁夏运行中 EC2 的性能指标,并检查今天有没有关机操作"
EXTRA=()

while [ $# -gt 0 ]; do
  case "$1" in
    --live) LIVE=1; shift ;;
    --region) REGION="$2"; shift 2 ;;
    --question) QUESTION="$2"; shift 2 ;;
    --json) EXTRA+=(--json); shift ;;
    *) echo "用法: $0 [--live] [--region cn-northwest-1] [--question '...'] [--json]"; exit 2 ;;
  esac
done

export LAB_LIVE="$LIVE" LAB_REGION="$REGION" PYTHONPATH="$PWD"
[ "$LIVE" = "1" ] && echo "模式: 真实只读查询 ($REGION)" || echo "模式: 离线(固定数据)"

pids=()
cleanup() {
  for pid in "${pids[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup EXIT

for expert in monitoring cloudtrail; do
  python3 expert.py "$expert" &
  pids+=("$!")
done

# 等专家就绪(轮询 Agent Card,不是盲等固定秒数)
for port in 9001 9002; do
  for _ in $(seq 1 25); do
    if curl -fsS "http://127.0.0.1:$port/.well-known/agent-card.json" >/dev/null 2>&1; then break; fi
    sleep 0.2
  done
done
echo

python3 supervisor.py "$QUESTION" ${EXTRA[@]+"${EXTRA[@]}"}
