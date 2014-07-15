:: This Win32 shell script removes files that need not be archived (.hex are kept)

@echo # preparing to delete these files:

@dir/B/OE *.csv 2>NUL:

@echo # to confirm deletion, press enter; else press Ctrl-C
@pause
@prompt $G
del/Q *.csv 2>NUL:

@echo # done..
@pause