import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
from os.path import exists

from dvrip.errors import DVRIPDecodeError, DVRIPRequestError
from dvrip_download import get_start_end, download_files, TIME_FMT
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
DNL_DELAY = timedelta(minutes=8)


def process_finished_files():
    global finished_files
    if len(finished_files) > 0:
        try:
            finished_file = finished_files[0]
            ip_address = finished_file['camip'][0]
            ip4 = ip_address.split('.')[3]
            name = finished_file['name'][0]
            device_work_dir = os.path.join(work_dir, name)
            event_time_str = finished_file['event_time'][0]
            event_time = datetime.strptime(event_time_str, TIME_FMT)
            bat_fn = ip4 + event_time.strftime(BAT_FILE_TIME_FMT) + '.bat'
            if 'run_bat' not in finished_file or finished_file['run_bat'][0] == '1':
                logging.info(f'% Now running {bat_fn} [{len(finished_files)}]')
                process = subprocess.Popen(os.path.join(device_work_dir, bat_fn),
                                           cwd=device_work_dir,
                                           creationflags=subprocess.CREATE_NEW_CONSOLE)
                process.wait()
                logging.info(f'% Finished running {bat_fn} [{len(finished_files)-1}]')
            else:
                logging.info(f'% Skip running {bat_fn} [{len(finished_files)-1}]')
        except Exception as e:
            logging.error(e)
        finally:
            finished_files = finished_files[1::]


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
                run_download = 'run_download' not in qs or qs['run_download'][0] == '1'
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
                if run_download and datetime.now() - event_time < DNL_DELAY:
                    logging.info(f"# Delayed download start time {event_time + DNL_DELAY}")
                    while datetime.now() - event_time < DNL_DELAY:
                        process_finished_files()
                        time.sleep(60)
            except Exception as e:
                logging.error(e)
                download_files_queue = download_files_queue[1::]
                logging.info(f'- Removing {msg} from the queue ({len(download_files_queue)})')
            else:
                try:
                    if not run_download:
                        finished_files.append(qs)
                        download_files_queue = download_files_queue[1::]
                        logging.info(f"- Downloading of {msg} not requested ({len(download_files_queue)})")
                    else:
                        logging.info(f"^ Started downloading of {msg} ({len(download_files_queue)})")
                        last_step = datetime.now()
                        k = download_files(ip_address, user, password, event_time, work_dir=cur_dir)
                        finished_files.append(qs)
                        download_files_queue = download_files_queue[1::]
                        logging.info(f"- Finished downloading {k} files on {msg} ({len(download_files_queue)})")
                except DVRIPDecodeError as e:
                    download_files_queue = download_files_queue[1::]
                    logging.error(f'  Incorrect credentials {e} ({len(download_files_queue)})')
                except DVRIPRequestError as e:
                    logging.error(e)
                    download_files_queue = download_files_queue[1::]
                except Exception as e:
                    logging.error(e)
                    if len(download_files_queue) > 1:
                        logging.info(f'- Try next from the queue ({len(download_files_queue)})')
                        download_files_queue = download_files_queue[1::] + download_files_queue[0:1:]
                    logging.info('# Retry in 30 sec')
                    time.sleep(30)
            if len(download_files_queue) == 0:
                process_finished_files()
        else:
            process_finished_files()
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
            s = "GET request from {} for {}".format(self.client_address, self.path)
            logging.info(s)
            self.query = parse_qs(urlparse(self.path).query)
            self.create_bat_and_json()
            self._set_response()
            self.wfile.write(s.encode('utf-8'))
        except Exception as e:
            logging.error(f'  Incorrect GET request "{e}"')
        else:
            if 'reinstall_service' in self.query and self.query['reinstall_service'][0] == '1':
                reinstall_service()
            else:
                self.download()

    def do_POST(self):
        try:
            s = "POST request from {} for {}".format(self.client_address, self.path)
            logging.info(s)
            self.query = parse_qs(urlparse(self.path).query)
            content_length = int(self.headers['Content-Length'])  # <--- Gets the size of data
            if content_length == 0:
                self.create_bat_and_json()
            else:
                post_data = self.rfile.read(content_length)  # <--- Gets the data itself
                self.create_bat_and_json(json.loads(post_data.decode('utf-8')))
            self.wfile.write(s.encode('utf-8'))
            self._set_response()
        except Exception as e:
            logging.error(f'  Incorrect POST request: "{e}"')
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
                    logging.info(f"+ Adding {mes} to the queue ({len(download_files_queue)})")
                    download_files_queue.append(self.query)
                else:
                    logging.info(f"~ The query {mes} is already in some list")
        except Exception as e:
            logging.warning(f'  Ignore incorrect request: there is no {e}')

    def create_bat_and_json(self, js=None):
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
        find_objects = 'find_objects' not in self.query or self.query['find_objects'] == '1'
        crop = None
        if 'crop' in self.query:
            crop = self.query['crop'][0]
        if js is not None:
            with open(os.path.join(device_work_dir, bat_fn + '.json'), 'wt') as out:
                out.write(json.dumps(js, indent=4, sort_keys=True))
        with open(os.path.join(device_work_dir, bat_fn + '.bat'), 'wt') as out:
            out.write('IF not exist trash_bin mkdir trash_bin\n')
            if out_fn2 is None:
                user = self.query['user'][0]
                password = self.query['password'][0]
                out.write(f'dvrip_download.exe {ip_address} {user} {password} {event_time_str} 0\n')
                out.write(f'call h264_separate.bat {out_fn}.h264 0\n')
                out.write(f'ren {out_fn}.mp4 {bat_fn}.mp4\n')
                if find_objects:
                    out.write(f'find_objects {bat_fn}.mp4\n')
                    out.write(f'if exist {bat_fn}-aicut.bat (\n')
                    out.write(f' call {bat_fn}-aicut.bat (\n')
                    out.write(f') else (\n')
                if crop is not None:
                    flt = f'-c:v h264 -b:v 3M -maxrate 5M -bufsize 2M -filter:v "crop={crop}"'
                else:
                    flt = '-c:v copy'
                out.write(f' ffmpeg.exe -hide_banner -y -i {bat_fn}.mp4 {flt} -c:a copy {bat_fn}-top.mp4\n')
                if find_objects:
                    out.write(')\n')
                out.write(f'move {bat_fn}.mp4 trash_bin\n')
            else:
                out.write(f'call dvrip_download.bat {bat_fn}\n')
                out.write(f'call h264_separate.bat {out_fn}.h264 0\n')
                out.write(f'call h264_separate.bat {out_fn2}.h264 0\n')
                out.write(f'(echo file {out_fn}.mp4 & echo file {out_fn2}.mp4)>list.txt\n')
                out.write(
                    f'ffmpeg.exe -hide_banner -f h264 -f concat -safe 0 -y -i list.txt -c:v copy -c:a copy {bat_fn}.mp4\n')
                out.write('del list.txt\n')
                sec = event_time.second
                if sec >= 30:
                    sec = sec - 30
                else:
                    sec = sec + 30
                if find_objects:
                    out.write(f'find_objects {bat_fn}.mp4\n')
                    out.write(f'if exist {bat_fn}-aicut.bat (\n')
                    out.write(f' call {bat_fn}-aicut.bat (\n')
                    out.write(f') else (\n')
                if crop is not None:
                    flt = f'-filter:v "crop={crop}"'
                else:
                    flt = ''
                out.write(f' ffmpeg.exe -hide_banner -y -i {bat_fn}.mp4 -ss 0:0:{sec} -t 0:1:0 {flt} '
                          f'-c:v h264 -b:v 3M -maxrate 5M -bufsize 2M -c:a copy {bat_fn}-top.mp4\n')
                if find_objects:
                    out.write(')\n')
                out.write(f'IF x%1x==xdx del {out_fn2}.h264\n')
                out.write(f'move {bat_fn}.mp4 trash_bin\n')
                out.write(f'move {out_fn}.mp4 trash_bin\n')
            out.write(f'IF x%1x==xdx del {out_fn}.h264\n')
            if out_fn2 is not None:
                out.write(f'move {out_fn2}.mp4 trash_bin\n')
            out.write(f'move {bat_fn} trash_bin\n')
            out.write(f'move {bat_fn}-cut.mp4 ../GDLink\n')
            out.write(f'move {bat_fn}.json trash_bin\n')
            out.write(f'move {bat_fn}*.bat trash_bin\n')


dvrip_load_on_run = 'dvrip_load_on_run.json'


def run(server_class=HTTPServer, handler_class=MyRequestHandler, port=8080):
    global work_dir, dvrip_load_on_run, download_files_queue, finished_files
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

    logging.info(f'<= Starting DVRIP http server on port {port} =>')
    if exists(dvrip_load_on_run):
        try:
            with open(dvrip_load_on_run, 'rt') as f:
                [download_files_queue, finished_files] = json.loads(f.read())
            logging.info(
                f'~ On server start the queue ({len(download_files_queue)})-[{len(finished_files)}] has been loaded')
        except Exception as e:
            logging.error(e)
        finally:
            os.remove(dvrip_load_on_run)

    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    save_queue()
    httpd.server_close()
    logging.info('<= Stopping httpd =>\n')


def save_queue():
    global work_dir, dvrip_load_on_run, download_files_queue, finished_files
    if len(download_files_queue) + len(finished_files) > 0:
        logging.info(f'~ Saving the queue ({len(download_files_queue)})-[{len(finished_files)}] to {dvrip_load_on_run}')
        with open(os.path.join(work_dir, dvrip_load_on_run), 'wt') as f:
            f.write(json.dumps([download_files_queue, finished_files]))
        download_files_queue = []
        finished_files = []


def reinstall_service():
    global download_files_queue
    logging.warning('! Service ReInstallation')
    download_files_queue = download_files_queue[1::] + download_files_queue[0:1:]
    save_queue()
    subprocess.Popen(os.path.join(work_dir, 'DvripService-reinstall-start.bat'),
                     creationflags=subprocess.CREATE_NEW_CONSOLE)


def daemon():
    global last_step, download_files_queue
    dnl_thread = threading.Thread(target=process_download_files_queue)
    dnl_thread.start()
    time.sleep(1)
    while True:
        if datetime.now() - last_step > timedelta(minutes=15):
            reinstall_service()
            break
        time.sleep(60)


if __name__ == '__main__':
    threading.Thread(target=daemon).start()

    if len(argv) == 3:
        work_dir = argv[2]

    # dvrip_load_on_run = os.path.join(work_dir, dvrip_load_on_run)

    if len(argv) >= 2:
        run(port=int(argv[1]))
    else:
        run()
