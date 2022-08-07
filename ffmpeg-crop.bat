ffmpeg.exe -hide_banner -f h264 -i %1 -filter:v "crop=%2:%3:0%4:0%5" %1-crop.mp4
