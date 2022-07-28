ffmpeg.exe -y -f alaw -f h264 -fflags +genpts+igndts -i %1 -ss 0:0:%2 -t 0:0:%3 -codec copy -c:a copy %1.mp4
