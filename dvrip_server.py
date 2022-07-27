import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging

from dvrip.errors import DVRIPDecodeError, DVRIPRequestError
from dvrip_download import download_file, download_files, TIME_FMT
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
import threading
import os
import json


work_dir = os.getcwdb().decode("utf-8")
download_files_queue = []
finished_files = []
skipped_files = []
FILE_TIME_FMT = '-%Y%m%d-%H%M'
last_step = datetime.now()
ONE_FILE_DELTA = 10


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
                start = datetime.strptime(qs['start'][0], TIME_FMT)
                msg = f"{ip_address} {start}"
                logging.info("^ Processing %s", msg)
                if start > datetime.now():
                    if qs not in skipped_files:
                        skipped_files.append(qs)
                    raise Exception('Start time greater than now')
                if 'sec' in qs:
                    sec = int(qs[f'sec'][0])
                else:
                    sec = 0
                need1 = 30 - ONE_FILE_DELTA <= sec <= 30 + ONE_FILE_DELTA
                if need1:
                    end = start + timedelta(minutes=1)
                else:
                    end = start + timedelta(minutes=2)
                    start = start - timedelta(minutes=1)

                while datetime.now() - end < timedelta(seconds=30):
                    last_step = datetime.now()
                    logging.info("# Need some sleep...")
                    time.sleep(30)
            except Exception as e:
                logging.error(e)
                download_files_queue = download_files_queue[1::]
                logging.info(f'- Removing {msg} from the queue')
            else:
                try:
                    logging.info("^ Started downloading of %s", msg)
                    for m in range(3):
                        last_step = datetime.now()
                        k = download_files(ip_address, user, password, start, end, work_dir=work_dir)
                        logging.info("- Finished downloading %i files on %s", k, msg)
                        if (need1 and k == 1) or (k >= 3):
                            break
                        else:
                            logging.info("^ Restart N%i downloading of %s in 1 min", m+1, msg)
                            time.sleep(60)
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
                        download_files_queue = download_files_queue[1::]+download_files_queue[0:1:]
                    logging.info('# Retry in 30 sec')
                    time.sleep(30)
            if len(download_files_queue) == 0:
                logging.info("  The download queue is empty :)")
        else:
            time.sleep(10)
            for sf in skipped_files:
                if sf not in download_files_queue:
                    start = datetime.strptime(sf['start'][0], TIME_FMT)
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
            mes = f"{self.query['camip'][0]} {self.query['start'][0]}"
            if self.query['start'][0].lower() == 'now':
                self.query['start'][0] = datetime.now().replace(second=0).strftime(TIME_FMT)
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
        ip_address = self.query['camip'][0]
        sec = int(self.query[f'sec'][0])
        s = self.query['start'][0]
        start = datetime.strptime(s, TIME_FMT)
        ip4 = ip_address.split('.')[3]
        out_fn = ip4 + start.strftime(FILE_TIME_FMT)
        out_fns = None
        if not ((30 - ONE_FILE_DELTA) < sec < (30 + ONE_FILE_DELTA)):
            out_fns = [ip4 + (start - timedelta(minutes=1)).strftime(FILE_TIME_FMT),
                       ip4 + (start + timedelta(minutes=1)).strftime(FILE_TIME_FMT)]
        crop = None
        if 'crop' in self.query:
            crop = self.query['crop'][0]
        if js is not None:
            js['sec'] = sec
            with open(os.path.join(work_dir, out_fn + '.json'), 'w') as out:
                out.write(json.dumps(js, indent=4, sort_keys=True))
        with open(os.path.join(work_dir, out_fn + '.bat'), 'w') as out:
            if crop is not None:
                flt = f'-filter:v "crop={crop}"'
            else:
                flt = ''
            if out_fns is None:
                user = self.query['user'][0]
                password = self.query['password'][0]
                out.write(f'dvrip_download.exe {ip_address} {user} {password} {s} 0\n')
                out.write(f'ffmpeg.exe -y -f h264 -i {out_fn}.h264 -codec copy {out_fn}.mp4"\n')
                if crop is not None:
                    out.write(f'ffmpeg.exe -y -i {out_fn}.mp4 {flt} {out_fn}-top.mp4\n')
            else:
                out.write(f'call dvrip_download.bat {out_fn}\n')
                out.write(
                    f'(echo file {out_fns[0]}.h264 & echo file {out_fn}.h264  & echo file {out_fns[1]}.h264)>list.txt\n')
                out.write(f'ffmpeg.exe -f h264 -f concat -safe 0 -y -i list.txt -codec copy {out_fn}.mp4\n')
                out.write('del list.txt\n')
                if sec >= 30:
                    min_sec = f'1:{sec - 30}'
                else:
                    min_sec = f'0:{sec + 30}'
                out.write(f'ffmpeg.exe -y -i {out_fn}.mp4 -ss 0:{min_sec} -t 0:1:0 {flt} {out_fn}-top.mp4\n')
                for fn in out_fns:
                    out.write(f'IF x%1x==xdx del {fn}.h264\n')
            out.write(f'IF x%1x==xdx del {out_fn}.h264\n')
            out.write(f'IF x%1x==xdx del {out_fn}.mp4\n')


def run(server_class=HTTPServer, handler_class=MyRequestHandler, port=8080):
    global work_dir
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                        level=logging.INFO,
                        datefmt='%d-%m-%Y %H:%M:%S',
                        filename=os.path.join(work_dir, 'dvrip_server.log'),
                        )
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info(f'=== Starting httpd on port {port} =====\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('... Stopping httpd ...\n')


def daemon():
    global last_step
    dnl_thread = threading.Thread(target=process_download_files_queue)
    dnl_thread.start()
    time.sleep(1)
    while True:
        if datetime.now() - last_step > timedelta(minutes=30):
            logging.warning('!!! Daemon needs to restart the download thread !!!\n')
            dnl_thread = threading.Thread(target=process_download_files_queue)
            dnl_thread.start()
            last_step = datetime.now()
        else:
            time.sleep(60)


if __name__ == '__main__':
    from sys import argv

    threading.Thread(target=daemon).start()

    if len(argv) == 3:
        work_dir = argv[2]

    if len(argv) >= 2:
        run(port=int(argv[1]))
    else:
        run()
