set fn=%1
set fnne=%~n1
set ext=%~x1
mkdir %fnne%
rem ffmpeg.exe -hide_banner -i %fn% -vf "select=not(mod(n\,10))" -vsync vfr %fnne%\frame-%%03d.jpg
ffmpeg.exe -hide_banner -i %fn% -r 1 -f image2 %fnne%\frame-%%03d.jpg
