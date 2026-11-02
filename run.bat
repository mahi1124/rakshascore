@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo  RakshaScore - Cyber Risk Assessment
echo ============================================

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creating virtual environment with Python 3.12...
    py -3.12 -m venv .venv
    if errorlevel 1 (
        echo ERROR: Python 3.12 was not found. Install it from https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

echo [2/4] Checking dependencies...
".venv\Scripts\python.exe" -c "import streamlit, rakshascore" >nul 2>&1
if errorlevel 1 (
    echo       Installing requirements ^(first run may take a few minutes^)...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    ".venv\Scripts\python.exe" -m pip install -e .
    if errorlevel 1 (
        echo ERROR: Dependency installation failed.
        pause
        exit /b 1
    )
)

if not exist "models\cyber_risk_best_model_10k.pkl" (
    echo [3/4] Model files missing - training now...
    ".venv\Scripts\python.exe" scripts\train_models.py
    if errorlevel 1 (
        echo ERROR: Model training failed.
        pause
        exit /b 1
    )
) else (
    echo [3/4] Model files found.
)

echo [4/4] Starting RakshaScore at http://localhost:8501
".venv\Scripts\python.exe" -m streamlit run app.py

pause
