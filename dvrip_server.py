from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer

from datetime import datetime, timedelta
from socket import AF_INET, SOCK_STREAM, socket as Socket
from sys import argv, stderr
from dvrip import DVRIP_PORT
from dvrip.io import DVRIPClient
from dvrip.files import FileType
import time
from os.path import exists
from pathlib import Path


def run(server_class=HTTPServer, handler_class=BaseHTTPRequestHandler):
    server_address = ('', 8008)
    httpd = server_class(server_address, handler_class)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


class HttpGetHandler(BaseHTTPRequestHandler):
    """Обработчик с реализованным методом do_GET."""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write('<html><head><meta charset="utf-8">'.encode())
        self.wfile.write('<title>Простой HTTP-сервер.</title></head>'.encode())
        self.wfile.write('<body>Был получен GET-запрос.</body></html>'.encode())


    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write('<html><head><meta charset="utf-8">'.encode())
        self.wfile.write('<title>Простой HTTP-сервер.</title></head>'.encode())
        self.wfile.write('<body>Был получен GET-запрос.</body></html>'.encode())


def download(dvrip_file):
    sock = Socket(AF_INET, SOCK_STREAM)
    sock.connect((argv[1], DVRIP_PORT))
    s = conn.download_file(sock, dvrip_file)
    ln = dvrip_file.length
    out_fn = ip_address.split('.')[3] + dvrip_file.start.strftime('-%Y%m%d-%H%M.h264')
    suffix = f'Complete of {ln}kb'
    i = 0
    if exists(out_fn):
        i = Path(out_fn).stat().st_size // 1024
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
                    print_progress_bar(i, ln, prefix=out_fn, suffix=suffix)
                    conn.keepalive()
                    time.sleep(0.01)
            print_progress_bar(i, i, prefix=out_fn, suffix=suffix)
            out.close()
        s.close()

run(handler_class=HttpGetHandler)