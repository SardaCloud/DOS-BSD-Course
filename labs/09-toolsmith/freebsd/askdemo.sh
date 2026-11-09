#!/bin/sh
# askdemo.sh -- (starter) act on the answer of ask.sh.  Compare ASKDEMO.BAT:
# case tests the exact value of $?, so the order of the branches does not
# matter.

sh "$(dirname "$0")/ask.sh" ynq Delete the old copies
# TODO: a case statement on $? that prints "Deleting (yes)", "Keeping them
# (no)", "Stopping here (quit)", "No answer: end of input" or "ask.sh failed".
