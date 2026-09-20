#!/bin/zsh
cd "$(dirname "$0")"
python3 safari_ad5m_bridge.py &
PID=$!
sleep 1
open -a Safari http://127.0.0.1:8765
wait $PID
