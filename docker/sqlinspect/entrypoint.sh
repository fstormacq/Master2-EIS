#!/bin/sh
# Start a virtual X server, run SQLInspect, then stop the X server.
# The CLI is an Eclipse application: without a display it crashes on exit
# (gtk_init_check() failed). xvfb-run is not used because it hangs when it
# runs as PID 1 in a container.
set -eu
export DISPLAY=:99
Xvfb "$DISPLAY" -screen 0 1024x768x24 -nolisten tcp >/dev/null 2>&1 &
XVFB_PID=$!
trap 'kill "$XVFB_PID" 2>/dev/null || true' EXIT
# Wait until the X server accepts connections (max ~10 s)
i=0
while [ ! -e /tmp/.X11-unix/X99 ] && [ "$i" -lt 100 ]; do sleep 0.1; i=$((i + 1)); done
status=0
/opt/sqlinspect/sqlinspect "$@" || status=$?
exit "$status"
