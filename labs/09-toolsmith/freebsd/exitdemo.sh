#!/bin/sh
# exitdemo.sh -- what $? holds after each kind of command (section 9.4)
sh -c 'exit 44';        echo "after exit 44:        \$? = $?"
sh -c 'exit 300';       echo "after exit 300:       \$? = $?"
sh -c 'kill -TERM $$';  echo "after kill -TERM:     \$? = $?"
false;                  echo "after false:          \$? = $?"
echo hello >/dev/null;  echo "after echo:           \$? = $?"
nosuch 2>/dev/null;     echo "after nosuch:         \$? = $?"
[ 1 -gt 2 ];            echo "after [ 1 -gt 2 ]:    \$? = $?"
if sh -c 'exit 3'; then echo "then branch"; else echo "else branch, \$? = $?"; fi
