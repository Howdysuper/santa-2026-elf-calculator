# Store lock shared by work/autoloop.sh and kaggle/watch_big.sh: only one of them writes best/ at a time.
# A lock older than 30 min of waiting is assumed stale and taken over.
store_lock() { for i in $(seq 1 90); do mkdir work/store.lock 2>/dev/null && return 0; sleep 20; done; echo "lock: taking over a stale lock"; return 0; }
store_unlock() { rmdir work/store.lock 2>/dev/null; }
