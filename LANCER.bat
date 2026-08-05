@echo off
rem ============================================================================
rem  Suivi des bons de livraison Lafarge
rem
rem  Double-cliquez sur ce fichier. La premiere utilisation installe ce qu'il
rem  faut (une minute environ), les suivantes demarrent immediatement.
rem
rem  Usages avances, depuis une invite de commandes :
rem    LANCER.bat demo                        jeu de factures d'essai
rem    LANCER.bat diagnostic "C:\...\fac.pdf" contenu detaille d'un PDF
rem ============================================================================
setlocal
cd /d "%~dp0"

set "VENV=%~dp0.venv"
set "PY=%VENV%\Scripts\python.exe"

set "LANCEUR="
where py >nul 2>&1 && set "LANCEUR=py -3"
if not defined LANCEUR where python >nul 2>&1 && set "LANCEUR=python"
if not defined LANCEUR goto :pas_de_python

if not exist "%PY%" (
    echo.
    echo Premiere utilisation : installation en cours, merci de patienter...
    echo.
    %LANCEUR% -m venv "%VENV%"
    if errorlevel 1 goto :echec_installation
    "%PY%" -m pip install --upgrade pip --quiet
    "%PY%" -m pip install -r "%~dp0requirements.txt" --quiet
    if errorlevel 1 goto :echec_installation
    echo Installation terminee.
    echo.
)

"%PY%" -m src.main %*
set "CODE=%ERRORLEVEL%"
if not "%CODE%"=="0" (
    echo.
    echo L'outil s'est arrete sans produire de tableur (code %CODE%^).
    echo Lisez le message ci-dessus : il indique quoi corriger.
    echo.
    pause
)
exit /b %CODE%

:pas_de_python
echo.
echo Python n'est pas installe sur ce poste.
echo.
echo   1. Rendez-vous sur https://www.python.org/downloads/
echo   2. Telechargez Python pour Windows et lancez l'installation
echo   3. IMPORTANT : cochez "Add python.exe to PATH" sur le premier ecran
echo   4. Relancez ce fichier
echo.
echo Si votre service informatique n'autorise pas cette installation,
echo demandez-lui la version .exe autonome de cet outil, qui n'a besoin de rien.
echo.
pause
exit /b 1

:echec_installation
echo.
echo L'installation a echoue. Causes les plus frequentes :
echo   - pas d'acces a Internet, ou proxy de l'entreprise bloquant
echo   - droits insuffisants sur ce dossier
echo.
echo Supprimez le dossier .venv puis relancez, ou demandez la version .exe.
echo.
pause
exit /b 1
