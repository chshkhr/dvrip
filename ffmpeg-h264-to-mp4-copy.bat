FORFILES /S /M *.h264 /C "cmd /c ffmpeg.exe -f h264 -i @path -ss 0:0:0 -t 0:1:0 -codec copy -c:a libmp3lame @fname.mp4"
