#!/usr/bin/env python3
# pylint: disable=wildcard-import,unused-wildcard-import

from datetime import datetime, timedelta
from socket import AF_INET, SOCK_STREAM, socket as Socket
from sys import argv, stderr
from dvrip import DVRIP_PORT
from dvrip.io import DVRIPClient
from dvrip.files import FileType
import time
from os.path import exists
from pathlib import Path


# Print iterations progress
def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=60, fill='█', printEnd="\r"):
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
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=printEnd)
    # Print New Line on Complete
    if iteration == total:
        print()


def download_file(conn, ip_address, dvrip_file, progress=print_progress_bar):
    sock = Socket(AF_INET, SOCK_STREAM)
    sock.connect((ip_address, DVRIP_PORT))
    s = conn.download(sock, dvrip_file)
    ln = dvrip_file.length
    out_fn = ip_address.split('.')[3] + dvrip_file.start.strftime('-%Y%m%d-%H%M.h264')
    suffix = f'Complete of {ln}kb'
    i = 0
    if exists(out_fn):
        i = Path(out_fn).stat().st_size // 1024
    if progress is not None:
        progress(i, ln, prefix=out_fn, suffix=suffix)
    if i < ln:
        with open(out_fn, 'wb') as out:
            for i in range(ln):
                chunk = s.read(1024)
                if not chunk:
                    break
                out.write(chunk)
                out.flush()
                # conn.keepalive()
                if i % 500 == 0:
                    if progress is not None:
                        progress(i, ln, prefix=out_fn, suffix=suffix)
                    conn.keepalive()
                    time.sleep(0.01)
            if progress is not None:
                progress(i, i, prefix=out_fn, suffix=suffix)
            out.close()
        s.close()


def download_files(ip_address, user, password, start, end, progress=None):
    conn = DVRIPClient(Socket(AF_INET, SOCK_STREAM))
    conn.connect((ip_address, DVRIP_PORT), user, password)
    lst = list(conn.files(start=start,
                          end=end,
                          channel=0,
                          type=FileType.VIDEO))
    for fl in lst:
        download_file(conn, ip_address, fl, progress)
    conn.logout()


def main():
    # Print wait
    wait_sec = int(argv[5])
    for j in range(wait_sec):
        print_progress_bar(j, wait_sec, prefix="Wait: ", suffix=f"of {wait_sec}c")
        time.sleep(1)

    ip_address = argv[1]
    start = datetime.strptime(argv[4], '%d.%m.%y %H:%M')
    end = start + timedelta(minutes=2)
    start = start - timedelta(minutes=1)
    print(f'Camera: {ip_address}\nStart: {start}\n')

    download_files(ip_address, argv[2], argv[3], start, end, progress=print_progress_bar)


if __name__ == "__main__":
    main()
