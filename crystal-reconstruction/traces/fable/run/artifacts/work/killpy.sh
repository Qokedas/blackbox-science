#!/bin/bash
# kill python processes (argv0 is python) whose cmdline contains $1
for p in /proc/[0-9]*; do
  pid=${p#/proc/}
  [ "$pid" = "$$" ] && continue
  cl=$(tr '\0' ' ' < $p/cmdline 2>/dev/null)
  first=${cl%% *}
  case "$first" in
    *python*) case "$cl" in *"$1"*) echo "kill $pid: ${cl:0:80}"; kill -9 $pid;; esac;;
  esac
done
