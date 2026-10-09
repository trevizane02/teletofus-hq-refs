@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Instalando o que o gerador precisa...
py -m pip install -r requirements.txt
if errorlevel 1 python -m pip install -r requirements.txt
echo.
echo Pronto. Agora crie o arquivo chave.txt nesta pasta com a sua chave da API do Gemini.
pause
