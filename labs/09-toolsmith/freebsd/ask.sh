#!/bin/sh
# ask.sh -- (starter) ask a question and return the answer as the exit status.
# usage: ask.sh keys [prompt]          e.g.  ask.sh ynq Overwrite the old copy
# Prints "prompt [Y,N,Q]? ", reads a line and exits with 1 for the first key,
# 2 for the second, ...; 0 at the end of the input; 255 if there are no keys.
# Keys are not case-sensitive and only the first character of a line counts.
# On a terminal a wrong answer beeps and asks again; from a file or a pipe a
# line that starts with another character is skipped.

if [ -z "$1" ]; then
	echo "usage: ask.sh keys [prompt]" >&2
	exit 255
fi
keys=$(printf '%s' "$1" | tr '[:lower:]' '[:upper:]')
shift
list=$(printf '%s' "$keys" | sed 's/./&,/g; s/,$//')
prompt="${*:+$* }[$list]? "

printf '%s' "$prompt"
while IFS= read -r line; do
	c=${line%"${line#?}"}			# the first character
	c=$(printf '%s' "$c" | tr '[:lower:]' '[:upper:]')
	# TODO: if $c is one of the keys in $keys, echo it (only when standard
	# input is not a terminal: [ -t 0 ]) and exit with its position, 1 for
	# the first key.  Hint: ${keys%%"$c"*} is the part of $keys before $c.
	if [ -t 0 ]; then
		printf '\a%s' "$prompt"		# beep and ask again
	fi
done
echo						# end of input: no answer
exit 0
