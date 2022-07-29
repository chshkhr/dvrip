set fn=%1
h264_audio.exe %fn%
set fn=%fn:"=%
set fn=%fn:~0,-5%
ffmpeg -y -f alaw -ar 8000 -ac 1 -i %fn%.audio -c:a mp3 -ar 16000 %fn%.mp3
ffmpeg -y -f h264 -i %fn%.h264 -c:v copy %fn%.mp4
ffmpeg -y -i %fn%.mp4 -itsoffset 0%2 -i %fn%.mp3 -c:v copy -c:a mp3 %fn%-a.mp4
del %fn%.audio
del %fn%.mp3
del %fn%.mp4
ren %fn%-a.mp4 %fn%.mp4
