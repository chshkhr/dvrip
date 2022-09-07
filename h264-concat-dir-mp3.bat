IF not exist trash_bin mkdir trash_bin

FORFILES /M *.h264 /C "cmd /c call h264_separate.bat @file 0"
del list.txt
move trash_bin\*.mp3 .\
for /f %%i in ('FORFILES /M *.mp3 /C "cmd /c echo @fname"') do (echo file %%~i.mp3)>>list.txt
ffmpeg.exe -hide_banner -f h264 -f concat -safe 0 -y -i list.txt -c:a copy result.mp3
del list.txt
move ???-????????-????.mp3 trash_bin
move ???-????????-????.mp4 trash_bin
