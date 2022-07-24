#!/usr/bin/env python3
# pylint: disable=wildcard-import,unused-wildcard-import

from datetime import datetime, timedelta
from socket import AF_INET, SOCK_STREAM, socket as Socket
from sys import argv, stderr
from dvrip import DVRIP_PORT
from dvrip.io import DVRIPClient
from dvrip.files import FileType
from dvrip.monitor import *
from dvrip.ptz import PTZButton
import time

import dvrip.packet


# def _read(file, length, _read=dvrip.packet._read):  # pylint: disable=protected-access
# 	data = _read(file, length)
# 	print('recv', bytes(data) if data[:1].isascii() else data.hex(),
# 	      file=stderr, flush=True)
# 	return data
# dvrip.packet._read = _read  # pylint: disable=protected-access
#
# def _write(file, data, _write=dvrip.packet._write):  # pylint: disable=protected-access
# 	print('send', bytes(data) if data[:1].isascii() else data.hex(),
# 	      file=stderr, flush=True)
# 	return _write(file, data)
# dvrip.packet._write = _write  # pylint: disable=protected-access

# Print iterations progress
def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=60, fill='█', printEnd="\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=printEnd)
    # Print New Line on Complete
    if iteration == total:
        print()


# print(list(DVRIPClient.discover('', 1.0)))
wt = int(argv[5])
ip = argv[1]
start = datetime.strptime(argv[4], '%d.%m.%y %H:%M')
end = start + timedelta(minutes=1)
print(f'Camera: {ip}\nStart: {start}\n')

for i in range(wt):
    printProgressBar(i, wt, prefix="Wait: ", suffix=f"of {wt}c")
    time.sleep(1)

conn = DVRIPClient(Socket(AF_INET, SOCK_STREAM))
conn.connect((ip, DVRIP_PORT), argv[2], argv[3])
# print(conn.systeminfo())
# print(conn.storageinfo())
# print(conn.time(conn.time() - timedelta(seconds=0)))
# now = datetime.now()
lst = list(conn.files(start=start,  # datetime(2022, 7, 23, 8, 45, 0),
                      end=end,  # datetime(2022, 7, 23, 8, 55, 0),
                      channel=0,
                      type=FileType.VIDEO))
print(lst[0])
# entries = list(conn.log(start=now - timedelta(days=30), end=now))
# for e in entries:
# 	print(e)
# 	print(e.data)
# for p in set((e.type, e.data) for e in entries if isinstance(e.data, str)):
# 	print(p)
# conn.button(0, PTZButton.MENU)

# name = '/idea0/2022-07-22/001/00.00.00-00.05.00[R][@caa7][0].h264'
# name = '/idea0/2022-07-23/001/16.35.00-16.40.00[R][@70f2][0].h264'
fl = lst[0]
sock = Socket(AF_INET, SOCK_STREAM)
sock.connect((argv[1], DVRIP_PORT))
s = conn.download(sock, fl)
ln = fl.length
out_fn = ip.split('.')[3] + start.strftime('-%Y%m%d-%H%M.h264')
suffix = f'Complete of {ln}kb'
printProgressBar(0, ln, prefix=out_fn, suffix=suffix)
with open(out_fn, 'wb') as out:
    for i in range(ln):
        chunk = s.read(1024)
        if not chunk:
            break
        out.write(chunk)
        out.flush()
        # conn.keepalive()
        if i % 500 == 0:
            printProgressBar(i, ln, prefix=out_fn, suffix=suffix)
            conn.keepalive()
            time.sleep(0.01)
    printProgressBar(i, i, prefix=out_fn, suffix=suffix)
    out.close()
s.close()

# monitor = Monitor(action=MonitorAction.START,
#                  params=MonitorParams(channel=0,
#                                       stream=Stream.HD))
# claim = MonitorClaim(session=conn.session, monitor=monitor)
# request = DoMonitor(session=conn.session, monitor=monitor)
# in_ = conn.reader(sock, claim, request)
#
# with open('test.264', 'wb') as out:
# 	while True:
# 		chunk = in_.read(16)
# 		if not chunk: break
# 		out.write(chunk)
# 		out.flush()

# conn.reboot()
conn.logout()
