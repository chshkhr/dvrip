set fn=D:\pythonmy\dvrip\output\find_objects.exe
if exist %fn% (
  del find_objects.exe
  move %fn% .
)
