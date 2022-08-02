set fn=%1
set fnne=%~n1
set ext=%~x1
mkdir %fnne%
ffmpeg -i %fn% -vf "select=not(mod(n\,10))" -vsync vfr %fnne%\frame-%%03d.jpg