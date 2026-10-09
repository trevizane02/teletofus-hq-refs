@echo off
chcp 65001 >nul
cd /d "%~dp0"
set /p PAG=Qual pagina montar de novo? (nao gasta nada; ex.: 2 ou 2-32): 
py montar.py %PAG%
pause
