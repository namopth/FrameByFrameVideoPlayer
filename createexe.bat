@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

REM --- Configuration ---
SET VENV_DIR=.venv
SET PYTHON_SCRIPT=main.py
SET REQUIREMENTS_FILE=requirements.txt
SET OUTPUT_NAME=FrameByFrameVideoPlayer
REM Add any extra PyInstaller options here (e.g., --noconsole, --icon=app.ico)
SET PYINSTALLER_OPTIONS=--onedir --windowed --clean
REM --- End Configuration ---

ECHO ============================================
ECHO  PyInstaller EXE Builder with Venv
ECHO ============================================
ECHO.
ECHO Venv Directory: %VENV_DIR%
ECHO Python Script:  %PYTHON_SCRIPT%
ECHO Output Name:    %OUTPUT_NAME%
ECHO PyInstaller Opts: %PYINSTALLER_OPTIONS%
ECHO.

REM Check if Python script exists
IF NOT EXIST "%PYTHON_SCRIPT%" (
    ECHO ERROR: Python script '%PYTHON_SCRIPT%' not found!
    GOTO :ErrorExit
)

REM Check if venv exists, create if not
IF NOT EXIST "%VENV_DIR%\Scripts\activate.bat" (
    ECHO Virtual environment '%VENV_DIR%' not found. Creating...
    python -m venv %VENV_DIR%
    IF !ERRORLEVEL! NEQ 0 (
        ECHO ERROR: Failed to create virtual environment. Make sure Python is installed and in PATH.
        GOTO :ErrorExit
    )
    ECHO Virtual environment created successfully.
) ELSE (
    ECHO Virtual environment '%VENV_DIR%' found.
)
ECHO.

REM Activate the virtual environment
ECHO Activating virtual environment...
CALL "%VENV_DIR%\Scripts\activate.bat"
IF !ERRORLEVEL! NEQ 0 (
    ECHO ERROR: Failed to activate virtual environment.
    GOTO :ErrorExit
)
ECHO.

REM Install/Upgrade pip and install PyInstaller & requirements
ECHO Installing/Upgrading required packages...
python -m pip install --upgrade pip
pip install pyinstaller
IF !ERRORLEVEL! NEQ 0 (
    ECHO ERROR: Failed to install PyInstaller.
    GOTO :ErrorExit
)

IF EXIST "%REQUIREMENTS_FILE%" (
    ECHO Installing dependencies from %REQUIREMENTS_FILE%...
    pip install -r %REQUIREMENTS_FILE%
    IF !ERRORLEVEL! NEQ 0 (
        ECHO ERROR: Failed to install dependencies from %REQUIREMENTS_FILE%.
        GOTO :ErrorExit
    )
) ELSE (
    ECHO No %REQUIREMENTS_FILE% found, skipping dependency installation.
    ECHO Make sure all required packages are manually installed or listed in the file.
)
ECHO.

REM Run PyInstaller
ECHO Running PyInstaller...
ECHO Command: pyinstaller %PYINSTALLER_OPTIONS% --name "%OUTPUT_NAME%" "%PYTHON_SCRIPT%"
pyinstaller %PYINSTALLER_OPTIONS% --name "%OUTPUT_NAME%" "%PYTHON_SCRIPT%"
IF !ERRORLEVEL! NEQ 0 (
    ECHO ERROR: PyInstaller failed. Check the output above for details.
    GOTO :ErrorExit
)
ECHO.

REM Deactivate is usually called automatically when the script ends, but can be explicit
REM ECHO Deactivating virtual environment...
REM CALL deactivate

ECHO ============================================
ECHO  Build Successful!
ECHO ============================================
ECHO The executable '%OUTPUT_NAME%.exe' should be in the 'dist' folder.
ECHO.
GOTO :End

:ErrorExit
ECHO.
ECHO ********************************************
ECHO  Build Failed!
ECHO ********************************************
ECHO Please check the error messages above.
PAUSE
EXIT /B 1

:End
ECHO.
PAUSE
EXIT /B 0