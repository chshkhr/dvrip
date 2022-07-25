import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging

from dvrip.errors import DVRIPDecodeError, DVRIPRequestError
from dvrip_download import download_file, download_files
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
import threading
import os
import json

work_dir = os.getcwdb().decode("utf-8")
download_files_queue = []
finished_files = []
skipped_files = []
TIME_FMT = '%d.%m.%y-%H:%M'


def process_download_files_queue():
    global download_files_queue, skipped_files, finished_files
    global work_dir
    while True:
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
                end = start + timedelta(minutes=2)
                start = start - timedelta(minutes=1)
                while datetime.now() - end < timedelta(seconds=30):
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
                        k = download_files(ip_address, user, password, start, end, work_dir=work_dir)
                        logging.info("- Finished downloading %i files on %s", k, msg)
                        if k >= 3:
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
                    logging.info('# Retry in 10 sec')
                    time.sleep(10)
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
        self._set_response()
        s = "GET request from {} for {}".format(self.client_address, self.path)
        self.wfile.write(s.encode('utf-8'))
        logging.info(s)

        self.query = parse_qs(urlparse(self.path).query)
        self.download()

    def download(self):
        try:
            mes = f"{self.query['camip'][0]} {self.query['start'][0]}"
            if self.query not in download_files_queue and \
                    self.query not in finished_files and \
                    self.query not in skipped_files:
                logging.info(f"+ Adding {mes} to the queue")
                download_files_queue.append(self.query)
            else:
                logging.info(f"~ The query {mes} is already in some list")
        except Exception as e:
            logging.warning(f'  Ignore incorrect request: there is no {e}')

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])  # <--- Gets the size of data
        post_data = self.rfile.read(content_length)  # <--- Gets the data itself
        s = "POST request from {} for {}".format(self.client_address, self.path)
        self.wfile.write(s.encode('utf-8'))
        logging.info(s)
        self._set_response()
        self.query = parse_qs(urlparse(self.path).query)

        try:
            js = json.loads(post_data.decode('utf-8'))
            ip_address = self.query['camip'][0]
            start = datetime.strptime(self.query['start'][0], TIME_FMT)
            out_fn = os.path.join(work_dir, ip_address.split('.')[3] + start.strftime('-%Y%m%d-%H%M.json'))
            js['sec'] = self.query['sec'][0]
            with open(out_fn, 'w') as out:
                out.write(json.dumps(js, indent=4, sort_keys=True))
        except Exception as e:
            logging.error(e)

        self.download()


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


if __name__ == '__main__':
    from sys import argv

    x = threading.Thread(target=process_download_files_queue)
    x.start()

    if len(argv) == 3:
        work_dir = argv[2]

    if len(argv) >= 2:
        run(port=int(argv[1]))
    else:
        run()
