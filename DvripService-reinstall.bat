net stop DvripServer
nssm remove DvripServer confirm
nssm install DvripServer dvrip_server.exe
reg import dvrip_Server.reg
nssm reset DvripServer ObjectName
nssm set DvripServer Type SERVICE_INTERACTIVE_PROCESS
net start DvripServer