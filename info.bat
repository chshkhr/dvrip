set fn=%1
set fnne=%~dpn1
set ext=%~x1
ffprobe.exe -hide_banner %fn% > %fn%.txt 2>&1
