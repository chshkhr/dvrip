(echo file %1 & echo file %2  & echo file %3)>concatlist.txt
D:\Portables\ffmpeg\ffmpeg.exe -f concat -safe 0 -i concatlist.txt -codec copy %4.mp4"
del concatlist.txt