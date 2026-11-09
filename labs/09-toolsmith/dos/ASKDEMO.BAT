@ECHO OFF
REM ASKDEMO.BAT -- (starter) act on the answer of ASK.
ASK YNQ Delete the old copies
REM TODO: jump to :FAILED, :QUIT, :NO or :YES with IF ERRORLEVEL n GOTO.
REM       IF ERRORLEVEL n is true for every exit code of n or more, so the
REM       order of the tests matters.  Exit code 0 falls through to the ECHO.
ECHO No answer: end of input or Ctrl-C
GOTO END
:YES
ECHO Deleting (yes)
GOTO END
:NO
ECHO Keeping them (no)
GOTO END
:QUIT
ECHO Stopping here (quit)
GOTO END
:FAILED
ECHO ASK failed
:END
