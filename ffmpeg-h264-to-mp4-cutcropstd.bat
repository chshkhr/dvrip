ffmpeg.exe -f h264 -i %1 -ss 0:0:%2 -t 0:0:%3 -filter:v "crop=2292:800:300:0" %1-top.mp4"
