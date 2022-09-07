IF not exist trash_bin mkdir trash_bin
set fn=%1
h264_separate.exe %fn%
set fn=%fn:"=%
set fn=%fn:~0,-5%
ffmpeg -y -f alaw -ar 8000 -ac 1 -i %fn%.audio -c:a mp3 -ar 16000 %fn%.mp3
ffmpeg -y -f h264 -i %fn%.video -c:v copy %fn%.mp4
ffmpeg -y -i %fn%.mp4 -itsoffset 0%2 -i %fn%.mp3 -c:v copy -c:a copy %fn%-a.mp4
del %fn%.audio
del %fn%.video
move %fn%.mp3 trash_bin
del %fn%.mp4
ren %fn%-a.mp4 %fn%.mp4