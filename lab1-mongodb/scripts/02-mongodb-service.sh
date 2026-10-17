#!/usr/bin/env bash
set -Eeuo pipefail

action="${1:-}"
case "$action" in
  start|stop|restart)
    systemctl "$action" mongod
    systemctl is-active mongod || [[ "$action" == "stop" ]]
    ;;
  status)
    systemctl status mongod --no-pager
    ;;
  *)
    echo "Использование: sudo $0 {start|stop|restart|status}" >&2
    exit 2
    ;;
esac

