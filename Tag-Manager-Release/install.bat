@echo off
echo Tag Manager インストーラー
echo ========================

REM 必要なディレクトリを作成
if not exist "%USERPROFILE%\AppData\Local\Tag-Manager" mkdir "%USERPROFILE%\AppData\Local\Tag-Manager"
if not exist "%USERPROFILE%\AppData\Local\Tag-Manager\resources" mkdir "%USERPROFILE%\AppData\Local\Tag-Manager\resources"

REM ファイルをコピー
copy "Tag-Manager.exe" "%USERPROFILE%\AppData\Local\Tag-Manager\"
copy "resources\*" "%USERPROFILE%\AppData\Local\Tag-Manager\resources\" /E /I /H /Y

REM デスクトップにショートカットを作成
echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
echo sLinkFile = "%USERPROFILE%\Desktop\Tag Manager.lnk" >> CreateShortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
echo oLink.TargetPath = "%USERPROFILE%\AppData\Local\Tag-Manager\Tag-Manager.exe" >> CreateShortcut.vbs
echo oLink.WorkingDirectory = "%USERPROFILE%\AppData\Local\Tag-Manager" >> CreateShortcut.vbs
echo oLink.Description = "Tag Manager" >> CreateShortcut.vbs
echo oLink.Save >> CreateShortcut.vbs
cscript //nologo CreateShortcut.vbs
del CreateShortcut.vbs

echo インストールが完了しました！
echo デスクトップにショートカットが作成されました。
pause
