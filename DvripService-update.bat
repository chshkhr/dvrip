net stop DvripServer
nssm remove DvripServer confirm
del grab\dvrip_Server.log

del dvrip_Server.exe
move D:\pythonmy\dvrip\output\dvrip_server.exe .

nssm install DvripServer dvrip_server.exe
reg import dvrip_Server.reg
nssm reset DvripServer ObjectName
nssm set DvripServer Type SERVICE_INTERACTIVE_PROCESS
net start DvripServer
