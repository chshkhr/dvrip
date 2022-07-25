(echo file %1 & echo file %2 )>concatlist.txt
D:\Portables\ffmpeg\ffmpeg.exe -f concat -safe 0 -i concatlist.txt -codec copy %3.mp4"
del concatlist.txt