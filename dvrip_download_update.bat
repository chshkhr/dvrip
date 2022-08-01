set fn=D:\pythonmy\dvrip\output\dvrip_download.exe
if exist %fn% (
  del dvrip_download.exe
  move %fn% .
)
