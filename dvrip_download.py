#!/usr/bin/env python3
# pylint: disable=wildcard-import,unused-wildcard-import

from datetime import datetime, timedelta
from socket import AF_INET, SOCK_STREAM, socket as Socket
from sys import argv
from dvrip import DVRIP_PORT
from dvrip.io import DVRIPClient
from dvrip.files import FileType
import time
from os.path import exists
from pathlib import Path
import os


TIME_FMT = '%d.%m.%y-%H:%M:%S'
ONE_FILE_DELTA = 10


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

BLK = 1024

def download_file(conn, ip_address, dvrip_file, progress=None, work_dir=''):
    sock = Socket(AF_INET, SOCK_STREAM)
    sock.connect((ip_address, DVRIP_PORT))
    # sock.settimeout(5)
    # sock.setblocking(False)
    s = conn.download(sock, dvrip_file)
    ln = dvrip_file.length
    video_fn = os.path.join(work_dir, ip_address.split('.')[3] + dvrip_file.start.strftime('-%Y%m%d-%H%M.h264'))
    suffix = f'Complete of {ln}kb'
    i = 0
    if exists(video_fn):
        i = Path(video_fn).stat().st_size // 1024
    if progress is not None:
        progress(i, ln, prefix=video_fn, suffix=suffix)
    if i < ln:
        with open(video_fn, 'wb') as video_out:
            for i in range(ln):
                chunk = s.read(BLK)
                if not chunk:
                    break
                video_out.write(chunk)
                if i % 200 == 0:
                    video_out.flush()
                    if progress is not None:
                        progress(i, ln, prefix=video_fn, suffix=suffix)
                    conn.keepalive()
                    time.sleep(0.01)
            if progress is not None:
                progress(i, i, prefix=video_fn, suffix=suffix)
            video_out.close()
        s.close()


def get_start_end(event_time):
    sec = event_time.second
    start = event_time.replace(second=0)
    end = start + timedelta(minutes=1)
    if sec < 30 - ONE_FILE_DELTA:
        start = start - timedelta(minutes=1)
    elif 30 + ONE_FILE_DELTA < sec:
        end = end + timedelta(minutes=1)
    end = end - timedelta(seconds=1)
    return [start, end]


def download_files(ip_address, user, password, event_time, progress=None, work_dir=''):
    conn = DVRIPClient(Socket(AF_INET, SOCK_STREAM))
    conn.connect((ip_address, DVRIP_PORT), user, password)

    [start, end] = get_start_end(event_time)

    lst = list(conn.files(start=start,
                          end=end,
                          channel=0,
                          type=FileType.VIDEO))
    for fl in lst:
        download_file(conn, ip_address, fl, progress=progress, work_dir=work_dir)
    conn.logout()
    return len(lst)


def main():
    # Print wait
    wait_sec = int(argv[5])
    for j in range(wait_sec):
        print_progress_bar(j, wait_sec, prefix="Wait: ", suffix=f"of {wait_sec}c")
        time.sleep(1)

    ip_address = argv[1]
    event_time = datetime.strptime(argv[4], TIME_FMT)
    print(f'Camera: {ip_address}\nEvent time: {event_time}\n')

    download_files(ip_address, argv[2], argv[3], event_time, progress=print_progress_bar)


if __name__ == "__main__":
    if len(argv) < 6:
        print('\nUsage: dvrip_download.exe cam_ip user password d.m.y-h:m:s wait_sec\n')
    else:
        main()
