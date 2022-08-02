set fn=%1
set fnne=%~dpn1
set ext=%~x1
ffmpeg -i %fn% -ss 0:0:%2 -t 0:0:%3 -c:a copy %fnne%-cut%ext% 