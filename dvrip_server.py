import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
from os.path import exists

from dvrip.errors import DVRIPDecodeError, DVRIPRequestError
from dvrip_download import get_start_end, download_files, TIME_FMT, ONE_FILE_DELTA
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
import threading
import os
import json
import subprocess
from sys import argv

from winreg import *

work_dir = os.getcwdb().decode("utf-8")
download_files_queue = []
finished_files = []
skipped_files = []
FILE_TIME_FMT = '-%Y%m%d-%H%M'
BAT_FILE_TIME_FMT = FILE_TIME_FMT + '-%S'
last_step = datetime.now()


def process_download_files_queue():
    global download_files_queue, skipped_files, finished_files
    global work_dir, last_step
    while True:
        last_step = datetime.now()
        if len(download_files_queue) > 0:
            try:
                qs = download_files_queue[0]
                ip_address = qs['camip'][0]
                user = qs['user'][0]
                password = qs['password'][0]
                if 'name' in qs:
                    name = qs['name'][0]
                    cur_dir = os.path.join(work_dir, name)
                    if not os.path.exists(cur_dir):
                        os.makedirs(cur_dir)
                event_time = datetime.strptime(qs['event_time'][0], TIME_FMT)
                msg = f"{ip_address} {event_time}"
                logging.info("^ Processing %s", msg)
                if event_time > datetime.now():
                    if qs not in skipped_files:
                        skipped_files.append(qs)
                    raise Exception('Start time greater than now')
                while datetime.now() - event_time < timedelta(minutes=8):
                    last_step = datetime.now()
                    logging.info("# Need some sleep...")
                    time.sleep(60)
            except Exception as e:
                logging.error(e)
                download_files_queue = download_files_queue[1::]
                logging.info(f'- Removing {msg} from the queue')
            else:
                try:
                    logging.info("^ Started downloading of %s", msg)
                    last_step = datetime.now()
                    k = download_files(ip_address, user, password, event_time, work_dir=cur_dir)
                    logging.info("- Finished downloading %i files on %s", k, msg)
                    finished_files.append(qs)
                    download_files_queue = download_files_queue[1::]
                except DVRIPDecodeError as e:
                    logging.error(f'  Incorrect credentials? {e}')
                    download_files_queue = download_files_queue[1::]
                except DVRIPRequestError as e:
                    logging.error(e)
                    download_files_queue = download_files_queue[1::]
                except Exception as e:
                    logging.error(e)
                    if len(download_files_queue) > 1:
                        logging.info('- Try another')
                        download_files_queue = download_files_queue[1::] + download_files_queue[0:1:]
                    logging.info('# Retry in 30 sec')
                    time.sleep(30)
            if len(download_files_queue) == 0:
                logging.info("  The download queue is empty :)")
        else:
            time.sleep(10)
            for sf in skipped_files:
                if sf not in download_files_queue:
                    start = datetime.strptime(sf['event_time'][0], TIME_FMT)
                    if start <= datetime.now():
                        download_files_queue.append(sf)
                        skipped_files = skipped_files[1::]
                        break
                else:
                    skipped_files = skipped_files[1::]
                    break


class MyRequestHandler(BaseHTTPRequestHandler):
    query = None

    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        try:
            self._set_response()
            s = "GET request from {} for {}".format(self.client_address, self.path)
            self.wfile.write(s.encode('utf-8'))
            logging.info(s)
            self.query = parse_qs(urlparse(self.path).query)
            self.create_bat_and_json()
        except Exception as e:
            logging.error(e)
        else:
            if 'reinstall_service' in self.query and self.query['reinstall_service'][0] == '1':
                reinstall_service()
            else:
                self.download()

    def do_POST(self):
        try:
            s = "POST request from {} for {}".format(self.client_address, self.path)
            self.wfile.write(s.encode('utf-8'))
            logging.info(s)
            self._set_response()
            self.query = parse_qs(urlparse(self.path).query)
            content_length = int(self.headers['Content-Length'])  # <--- Gets the size of data
            if content_length == 0:
                self.create_bat_and_json()
            else:
                post_data = self.rfile.read(content_length)  # <--- Gets the data itself
                self.create_bat_and_json(json.loads(post_data.decode('utf-8')))
        except Exception as e:
            logging.error(e)
        else:
            self.download()

    def download(self):
        try:
            if 'dont_load' in self.query and self.query['dont_load'][0] == '1':
                logging.info("- Download is not needed")
            else:
                mes = f"{self.query['camip'][0]} {self.query['event_time'][0]}"
                if self.query not in download_files_queue and \
                        self.query not in finished_files and \
                        self.query not in skipped_files:
                    logging.info(f"+ Adding {mes} to the queue")
                    download_files_queue.append(self.query)
                else:
                    logging.info(f"~ The query {mes} is already in some list")
        except Exception as e:
            logging.warning(f'  Ignore incorrect request: there is no {e}')

    def create_bat_and_json(self, js=None):
        try:
            ip_address = self.query['camip'][0]
            ip4 = ip_address.split('.')[3]
            if self.query['event_time'][0].lower() == 'now':
                self.query['event_time'][0] = datetime.now().strftime(TIME_FMT)
            name = self.query['name'][0]
            device_work_dir = os.path.join(work_dir, name)
            if not os.path.exists(device_work_dir):
                os.makedirs(device_work_dir)
            event_time_str = self.query['event_time'][0]
            event_time = datetime.strptime(event_time_str, TIME_FMT)
            [start, end] = get_start_end(event_time)
            bat_fn = ip4 + event_time.strftime(BAT_FILE_TIME_FMT)
            out_fn = ip4 + start.strftime(FILE_TIME_FMT)
            out_fn2 = None
            if end - start > timedelta(minutes=1):
                out_fn2 = ip4 + end.strftime(FILE_TIME_FMT)
            crop = None
            if 'crop' in self.query:
                crop = self.query['crop'][0]
            if js is not None:
                with open(os.path.join(device_work_dir, bat_fn + '.json'), 'w') as out:
                    out.write(json.dumps(js, indent=4, sort_keys=True))
            with open(os.path.join(device_work_dir, bat_fn + '.bat'), 'w') as out:
                if crop is not None:
                    flt = f'-filter:v "crop={crop}"'
                else:
                    flt = '-c:v copy'
                if out_fn2 is None:
                    user = self.query['user'][0]
                    password = self.query['password'][0]
                    out.write(f'dvrip_download.exe {ip_address} {user} {password} {event_time_str} 0\n')
                    out.write(f'call h264_separate.bat {out_fn}.h264 0\n')
                    if crop is not None:
                        out.write(f'ffmpeg.exe -y -i {out_fn}.mp4 {flt} {bat_fn}-top.mp4\n')
                else:
                    out.write(f'call dvrip_download.bat {bat_fn}\n')
                    out.write(f'call h264_separate.bat {out_fn}.h264 0\n')
                    out.write(f'call h264_separate.bat {out_fn2}.h264 0\n')
                    out.write(
                        f'(echo file {out_fn}.mp4 & echo file {out_fn2}.mp4)>list.txt\n')
                    out.write(
                        f'ffmpeg.exe -f h264 -f concat -safe 0 -y -i list.txt -codec copy -c:a copy {bat_fn}.mp4\n')
                    out.write('del list.txt\n')
                    sec = event_time.second
                    if sec >= 30:
                        sec = sec - 30
                    else:
                        sec = sec + 30
                    out.write(
                        f'ffmpeg.exe -y -i {bat_fn}.mp4 -ss 0:0:{sec} -t 0:1:0 {flt} -c:a copy {bat_fn}-top.mp4\n')
                    out.write(f'IF x%1x==xdx del {out_fn2}.h264\n')
                    out.write(f'del {bat_fn}.mp4\n')
                    out.write(f'del {out_fn}.mp4\n')
                out.write(f'IF x%1x==xdx del {out_fn}.h264\n')
                if out_fn2 is not None:
                    out.write(f'del {out_fn2}.mp4\n')
        except Exception as e:
            logging.error(f'  Json/bat processing error: {e}')


daemon_run_count = 0
dvrip_load_on_run = 'dvrip_load_on_run.json'


def run(server_class=HTTPServer, handler_class=MyRequestHandler, port=8080):
    global work_dir, dvrip_load_on_run, download_files_queue
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                        level=logging.INFO,
                        datefmt='%d-%m-%Y %H:%M:%S',
                        filename=os.path.join(work_dir, 'dvrip_server.log'),
                        )

    if argv[0].find('dvrip_server.py') < 0:
        try:
            a_key = r"SYSTEM\CurrentControlSet\Services\DvripServer\Parameters"
            a_reg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
            a_key = OpenKey(a_reg, a_key)
            work_dir = QueryValueEx(a_key, "AppDirectory")[0]
            # work_dir = os.path.abspath(os.path.join(work_dir, os.pardir))
            CloseKey(a_key)
        except Exception as e:
            logging.error(e)

    if exists(dvrip_load_on_run):
        try:
            with open(dvrip_load_on_run, 'rt') as f:
                download_files_queue = json.loads(f.read())
            logging.info(f'  On start loaded the queue with {len(download_files_queue)} tasks ')
        except Exception as e:
            logging.error(e)
        finally:
            os.remove(dvrip_load_on_run)

    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info(f'=== Starting httpd on port {port} =====\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('... Stopping httpd ...\n')
    save_queue()


def save_queue():
    global work_dir, dvrip_load_on_run, download_files_queue
    if len(download_files_queue) > 0:
        s = os.path.join(work_dir, dvrip_load_on_run)
        logging.info(f'  Saving the queue with {len(download_files_queue)} tasks to {s}\n')
        with open(s, 'wt') as f:
            f.write(json.dumps(download_files_queue))


def reinstall_service():
    logging.warning(' !!! Service Reinstall !!!')
    save_queue()
    subprocess.Popen(os.path.join(work_dir, 'DvripService-reinstall-start.bat'), creationflags=subprocess.CREATE_NEW_CONSOLE)


def daemon():
    global last_step, daemon_run_count, download_files_queue
    dnl_thread = threading.Thread(target=process_download_files_queue)
    dnl_thread.start()
    time.sleep(1)
    while True:
        if datetime.now() - last_step > timedelta(minutes=30):
            if daemon_run_count < 3:
                daemon_run_count += 1
                logging.warning(f'!!! ({daemon_run_count}) Daemon needs to restart the download thread !!!\n')
                dnl_thread = threading.Thread(target=process_download_files_queue)
                dnl_thread.start()
                last_step = datetime.now()
            else:
                reinstall_service()

        else:
            time.sleep(60)


if __name__ == '__main__':
    threading.Thread(target=daemon).start()

    if len(argv) == 3:
        work_dir = argv[2]

    dvrip_load_on_run = os.path.join(work_dir, dvrip_load_on_run)

    if len(argv) >= 2:
        run(port=int(argv[1]))
    else:
        run()
