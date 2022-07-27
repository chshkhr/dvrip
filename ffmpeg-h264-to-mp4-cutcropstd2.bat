ffmpeg.exe -f h264 -i %1 -ss 0:0:%2 -t 0:0:%3 -filter:v "crop=1500:1000:0:500" %1-bot.mp4"
