#!/bin/sh
# Lab 7.7: what msdosfs reports for files that have no owner, group, mode or inode number.
# Run as root in the FreeBSD 15.1 VM, with the lab floppy image copied to /tmp/dos400.img.
set -e
md=$(mdconfig -a -t vnode -o readonly -f /tmp/dos400.img)
ls -ld /mnt                                   # the mount point supplies the defaults
mount_msdosfs -o ro "/dev/$md" /mnt
ls -lio /mnt/IO.SYS /mnt/MSDOS.SYS /mnt/COMMAND.COM /mnt/CONFIG.SYS
umount /mnt
mount_msdosfs -o ro -u 1001 -g 1001 -m 644 "/dev/$md" /mnt
ls -lio /mnt/IO.SYS /mnt/MSDOS.SYS /mnt/COMMAND.COM /mnt/CONFIG.SYS
umount /mnt
mdconfig -d -u "${md#md}"
