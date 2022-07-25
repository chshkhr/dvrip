import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
from dvrip_download import download_file, download_files
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
import threading
import os

work_dir = os.getcwdb().decode("utf-8")
download_files_queue = []


def process_download_files_queue():
    global download_files_queue
    global work_dir
    while True:
        if len(download_files_queue) > 0:
            qs = download_files_queue[0]
            ip_address = qs['camip'][0]
            user = qs['user'][0]
            password = qs['password'][0]
            start = datetime.strptime(qs['start'][0], '%d.%m.%y-%H:%M')
            end = start + timedelta(minutes=2)
            start = start - timedelta(minutes=1)
            msg = f"{qs['camip'][0]} {qs['start'][0]}"
            while datetime.now() - end < timedelta(seconds=30):
                logging.info("# Need some sleep...")
                time.sleep(30)
            try:
                logging.info("^ Started downloading of %s", msg)
                download_files(ip_address, user, password, start, end, work_dir=work_dir)
                logging.info("- Finished downloading of %s", msg)
                download_files_queue = download_files_queue[1::]
            except Exception as e:
                logging.error(e)
                #logging.exception(e)
                logging.info('# Retry in 10 sec')
                time.sleep(10)
            if len(download_files_queue) == 0:
                logging.info("  Download queue is empty :)")
        else:
            time.sleep(1)


class MyRequestHandler(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        self._set_response()
        qs = parse_qs(urlparse(self.path).query)
        s = "GET request from {} for {}".format(self.client_address, self.path)
        self.wfile.write(s.encode('utf-8'))
        logging.info(s)
        if qs not in download_files_queue:
            download_files_queue.append(qs)
            logging.info("+ Adding %s %s to download queue", qs['camip'][0], qs['start'][0])
        else:
            logging.info("~ Query %s %s is already in list", qs['camip'][0], qs['start'][0])


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
