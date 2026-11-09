#!/bin/sh
# backup.sh -- copy the files that changed into a backup directory.
# Usage: backup.sh dir file...  (the shell expands patterns before we start)
# Exit status: 0 all copied or unchanged, 1 something failed, 2 usage.
# Starter (Lab 9.7): it runs, but it copies every file every time and
# always exits with 0. Complete TODO 1 to 3.

usage() {
	echo "usage: backup.sh dir file..." >&2
	exit 2
}

[ $# -ge 2 ] || usage
dir=$1
shift
[ -d "$dir" ] || usage

copied=0 same=0 failed=0

backup_one() {
	f=$1
	b=$dir/${f##*/}
	if [ ! -f "$f" ]; then
		echo "FAILED  $f"
		failed=$((failed + 1))
		return 1
	fi
	# TODO 1: if "$b" exists and "$f" is not newer than it (test -nt),
	# print "same", count it and return 0.
	# TODO 2: copy with cp -p inside an if; on failure print "FAILED",
	# count it and return 1.
	cp "$f" "$b"
	echo "copied  $f"
	copied=$((copied + 1))
}

for f in "$@"; do
	backup_one "$f"
done
echo "$copied copied, $same unchanged, $failed failed"
# TODO 3: make the exit status 1 when a file failed, else 0.
exit 0
