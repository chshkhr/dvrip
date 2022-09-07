IF not exist trash_bin mkdir trash_bin

FORFILES /M *.h264 /C "cmd /c call h264_separate.bat @file 0"
del list.txt
for /f %%i in ('FORFILES /M *.mp4 /C "cmd /c echo @fname"') do (echo file %%~i.mp4)>>list.txt
ffmpeg.exe -hide_banner -f h264 -f concat -safe 0 -y -i list.txt -c:v copy -c:a copy result.mp4
del list.txt
move ???-????????-????.mp4 trash_bin
