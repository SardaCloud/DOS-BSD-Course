@ECHO OFF
REM EL.BAT -- show the current ERRORLEVEL (0 to 3; 4 means 4 or more).
REM Run it with CALL EL. IF ERRORLEVEL n means "n or more", so the last
REM test that matches gives the value.
FOR %%N IN (0 1 2 3 4) DO IF ERRORLEVEL %%N SET EL=%%N
ECHO exit code %EL%
SET EL=
