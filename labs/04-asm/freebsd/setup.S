/* setup.S - section 4.3: boot-sector set-up code in AT&T syntax (as in boot0.S) */
        .code16
        .text
start:  cld
        xorw    %ax, %ax
        movw    %ax, %es
        movw    %ax, %ds
        movw    %ax, %ss
        movw    $0x7c00, %sp