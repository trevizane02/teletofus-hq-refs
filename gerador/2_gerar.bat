@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist chave.txt (echo Falta o arquivo chave.txt com a sua chave do Gemini. & pause & exit /b)
set /p GEMINI_API_KEY=<chave.txt
set /p PAG=Qual pagina gerar? (ex.: 2  ou  4-7  ou  capa): 
set /p REF=Refazer algum quadro? (numero, ou Enter para nao): 
if "%REF%"=="" (py gerar.py %PAG%) else (py gerar.py %PAG% --refazer %REF%)
echo.
echo As paginas prontas ficam em saida\vol4\
pause
