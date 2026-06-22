@echo off
chcp 65001 >nul

echo Dang khoi dong Server chup anh...
cd /d "E:\Download\VDII\Auto_Edit_Tool"
start "Capture Server" python capture_server.py
timeout /t 1 >nul

echo Dang mo cac tab tai lieu chinh (Ben trai)...
start chrome --new-window --window-position=0,0 --window-size=500,500 --profile-directory="Profile 5" ^
 "https://docs.google.com/spreadsheets/d/11qQUShH6VodnRmDTRX3k0y2hutwvAgPJcq89us1qkzQ/edit?gid=0#gid=0" ^
 "https://aeglobal.lotuslms.com/admin/content-manager/folder/690173da0de3cd4f2808c80e" ^
 "https://notebooklm.google.com/notebook/6b86d189-b723-44cb-81b8-e9fca8bcfcb3"
timeout /t 1 >nul

echo Dang mo Gemini (Goc phai tren)...
start chrome --new-window --window-position=500,0 --window-size=500,500 --profile-directory="Profile 5" "https://gemini.google.com/gem/507de5d07544"
timeout /t 1 >nul

echo Dang mo Auto Edit Tool (Goc phai duoi)...
start chrome --app="file:///E:/Download/VDII/Auto_Edit_Tool/data_processor.html" --window-position=1000,0 --window-size=500,500 --profile-directory="Profile 5"

start chrome --app="file:///E:/Download/VDII/Auto_Edit_Tool/index.html" --window-position=1000,0 --window-size=500,500 --profile-directory="Profile 5"

exit
