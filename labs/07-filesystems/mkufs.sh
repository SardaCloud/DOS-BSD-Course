#!/bin/sh
# Lab 7.5: a UFS2 file system on a 32 MB memory disk, and what the tools say about it.
# Run as root in the FreeBSD 15.1 VM:  sh mkufs.sh 2>&1 | tee mkufs.out
set -e
md=$(mdconfig -a -t malloc -s 32m)            # prints the new unit, e.g. md0
echo "memory disk: /dev/$md"
diskinfo -v "/dev/$md" | head -4
newfs -U "/dev/$md"                           # UFS2, soft updates, 32 KB blocks, 4 KB fragments
dumpfs -m "/dev/$md"                          # the newfs command that would recreate it
dumpfs "/dev/$md" | head -20                  # superblock fields
mount "/dev/$md" /mnt
mkdir /mnt/dir
echo hello > /mnt/dir/small.txt
dd if=/dev/random of=/mnt/big.bin bs=1k count=100 2>/dev/null
ln /mnt/dir/small.txt /mnt/hardlink.txt
ln -s dir/small.txt /mnt/symlink
ls -lia /mnt /mnt/dir
ino=$(stat -f %i /mnt/big.bin)                # fsdb -r refuses "cd" (see the text): use the number
umount /mnt
fsdb -r "/dev/$md" <<EOF
ls
inode $ino
blocks
quit
EOF
dd if="/dev/$md" of=/tmp/ufs32.img bs=1m 2>/dev/null   # keep a copy for ufsx.py on your computer
mdconfig -d -u "${md#md}"
echo "image saved in /tmp/ufs32.img"
