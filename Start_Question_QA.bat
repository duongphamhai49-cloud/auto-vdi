@echo off
chcp 65001 >nul

echo ========================================================
echo        DANG KHOI DONG QUESTION QA WORKSPACE
echo ========================================================

echo 1. Dang khoi dong Python Server (ho tro tim kiem va mo Edit LMS)...
cd /d "E:\Download\VDII\Auto_Edit_Tool"
start "LMS Search Server" python main_server.py
timeout /t 1 >nul

echo 2. Dang mo Lotus LMS va Gemini (Cua so moi - Profile 5)...
start chrome --new-window --profile-directory="Profile 5" ^
 "https://aeglobal.lotuslms.com/admin/content-manager/folder/690173da0de3cd4f2808c80e" ^
 "https://gemini.google.com/app?hl=vi"
timeout /t 1 >nul

echo 3. Dang mo Google Sheets (Cua so moi - Profile 18)...
start chrome --new-window --profile-directory="Profile 18" ^
 "https://docs.google.com/spreadsheets/d/1amVdj270BHPF0oY6euzRD07XkPe20BIjf-W2MWmG8Zw/edit?pli=1&gid=632975456#gid=632975456"
timeout /t 1 >nul

echo 4. Dang mo Question QA Tool...
start chrome --app="file:///E:/Download/VDII/Auto_Edit_Tool/question_qa.html" --profile-directory="Profile 5"

echo ========================================================
echo Khoi dong hoan tat!
exit
