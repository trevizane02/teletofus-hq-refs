@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist chave.txt (echo Falta o arquivo chave.txt com a sua chave do Gemini. & pause & exit /b)
echo Gerando a CAPA e as PAGINAS 2 a 5 e montando o PDF...
py gerar.py capa,2-5 --pdf
echo.
echo O PDF fica em saida\vol4\
start "" "saida\vol4"
pause
