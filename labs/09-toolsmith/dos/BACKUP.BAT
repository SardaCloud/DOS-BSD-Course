@ECHO OFF
REM BACKUP.BAT -- copy the files that changed into a backup directory.
REM Usage: BACKUP.BAT dir pattern [pattern ...]
REM Type the .BAT: a plain BACKUP runs A:\BACKUP.COM, which wins over .BAT.
REM Patterns name files in the current directory. Needs FC, XCOPY, FIND, RC.COM.
REM Exit code: 0 all copied or unchanged, 1 something failed, 2 usage.
REM Starter (Lab 9.7): it runs, but it copies every file every time and
REM always exits with 0. Complete TODO 1 to 3.
IF "%1"==":ONE" GOTO ONE
IF "%2"=="" GOTO USAGE
IF NOT EXIST %1\NUL GOTO USAGE
SET BAKBAT=%0
SET BAKDIR=%1
SET BAKFAIL=
TYPE NUL >%1\COPIED.LST
TYPE NUL >%1\SAME.LST
TYPE NUL >%1\FAILED.LST
:NEXT
SHIFT
IF "%1"=="" GOTO DONE
FOR %%F IN (%1) DO CALL %BAKBAT% :ONE %%F
GOTO NEXT

:DONE
FIND /C /V "?" %BAKDIR%\COPIED.LST %BAKDIR%\SAME.LST %BAKDIR%\FAILED.LST
SET BAKBAT=
SET BAKDIR=
REM TODO 3: exit with 1 (RC 1) if BAKFAIL is 1, else with 0; clear BAKFAIL.
RC 0
GOTO END

:USAGE
ECHO Usage: BACKUP.BAT dir pattern [pattern ...]
RC 2
GOTO END

REM CALL BACKUP.BAT :ONE name -- one file; BAKDIR is the backup directory.
:ONE
IF NOT EXIST %2 GOTO FAILED
REM TODO 1: if %BAKDIR%\%2 exists and FC /B finds no difference (exit
REM code 0), report "same", append the name to SAME.LST and GOTO END.
:COPY
REM TODO 2: XCOPY instead of COPY (COPY sets no ERRORLEVEL), and
REM GOTO FAILED when XCOPY's exit code is 1 or more.
COPY %2 %BAKDIR% >NUL
ECHO copied  %2
ECHO %2>>%BAKDIR%\COPIED.LST
GOTO END
:FAILED
ECHO FAILED  %2
ECHO %2>>%BAKDIR%\FAILED.LST
SET BAKFAIL=1
:END
