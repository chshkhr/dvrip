set fn=D:\pythonmy\dvrip\output\dvrip_server.exe
if exist %fn% (
net stop DvripServer
nssm remove DvripServer confirm
del grab\dvrip_Server.log

del dvrip_server.exe
move %fn% .

nssm install DvripServer dvrip_server.exe 8108
reg import dvrip_Server.reg
nssm reset DvripServer ObjectName
nssm set DvripServer Type SERVICE_INTERACTIVE_PROCESS
net start DvripServer
)

