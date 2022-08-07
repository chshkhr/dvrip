(echo file %1 & echo file %2 )>concatlist.txt
ffmpeg.exe -hide_banner -f concat -safe 0 -i concatlist.txt -codec copy %3.mp4"
del concatlist.txt