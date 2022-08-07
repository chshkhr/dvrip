import json
import os
import shutil
import subprocess
import time
from datetime import timedelta
from pathlib import Path
from sys import argv
from PIL import Image
import requests

serverPort = 5000
serverHost = "localhost"
serverUrl = f"http://{serverHost}:{serverPort}/v1/"
verifySslCert = False
minConfidence = 0.4
frame_max_x = None
frame_max_y = None
MARGIN = 0.1
margin_x = None
margin_y = None
OBJ_SET = ['person', 'car', 'cat', 'dog']
sleep_between_requests = 0.3


def process_dir(directory):
    global frame_max_x, frame_max_y, MARGIN, margin_x, margin_y, sleep_between_requests
    result_prediction = None
    index = None
    for file_name in os.listdir(directory):
        if file_name.endswith(".jpg"):
            filepath = os.path.join(directory, file_name)

            if frame_max_x is None:
                img = Image.open(filepath)
                frame_max_x, frame_max_y = img.size
                margin_x = round(frame_max_x * MARGIN)
                margin_y = round(frame_max_y * MARGIN)
                print(f'{frame_max_x}x{frame_max_y}')
                img.close()

            image_data = open(filepath, "rb").read()

            response = requests.post(
                serverUrl + "vision/detection",
                files={"image": image_data},
                data={"min_confidence": minConfidence},
                verify=verifySslCert
            ).json()

            if response['success']:
                predictions = response['predictions']
                if len(predictions) == 0:
                    os.remove(filepath)
                else:
                    for prediction in predictions:
                        label = prediction['label']
                        found = False
                        if label in OBJ_SET:
                            found = True
                            index = int(file_name[-7:-4])
                            print(f'Frame {index}: {label}')
                            if result_prediction is None:
                                result_prediction = prediction
                                result_prediction['first'] = index
                            else:
                                result_prediction['last'] = index
                                result_prediction['y_min'] = min(prediction['y_min'], result_prediction['y_min'])
                                result_prediction['x_min'] = min(prediction['x_min'], result_prediction['x_min'])
                                result_prediction['y_max'] = max(prediction['y_max'], result_prediction['y_max'])
                                result_prediction['x_max'] = max(prediction['x_max'], result_prediction['x_max'])
                                result_prediction['confidence'] = min(prediction['confidence'], result_prediction['confidence'])
                                if not prediction['label'] in result_prediction['label']:
                                    result_prediction['label'] += prediction['label']
                    if not found:
                        os.remove(filepath)
            if sleep_between_requests > 0:
                time.sleep(sleep_between_requests)
        else:
            continue
    if result_prediction is not None and index is not None:
        result_prediction['count'] = index
    return result_prediction


def extract_frames(file_name):
    process = subprocess.Popen(['ffmpeg-extract-frames.bat', file_name])
    process.wait()


def main():
    global frame_max_x, frame_max_y, MARGIN, margin_x, margin_y, sleep_between_requests
    in_file = argv[1]
    if len(argv) > 2:
        sleep_between_requests = float(argv[2])
    print('Extraction started\n')
    extract_frames(in_file)
    name = Path(in_file).stem
    print('AI Image Processing started\n')
    prediction = process_dir(name)
    if prediction is not None:
        print(prediction)
        y_max = prediction['y_max']
        x_min = prediction['x_min']
        x_max = prediction['x_max']
        y_min = prediction['y_min']
        wid = min(round((x_max - x_min) * (1 + MARGIN)), frame_max_x)
        hgt = min(round((y_max - y_min) * (1 + MARGIN)), frame_max_y)
        shift_x = max(x_min - margin_x//2, 0)
        shift_y = max(y_min - margin_y//2, 0)
        first = max(int(prediction['first'])-5, 0)
        count = int(prediction['count'])
        last = min(int(prediction['last'])+2,count)
        s = f'ffmpeg.exe -hide_banner -y -i {in_file} ' \
            f'-ss 0:{first//60}:{first%60} -t 0:{(last-first)//60}:{(last-first)%60} ' \
            f'-filter:v "crop={wid}:{hgt}:{shift_x}:{shift_y}" ' \
            f'-c:v h264 -b:v 3M -maxrate 5M -bufsize 2M ' \
            f'-c:a copy {name}-cut.mp4'
        print(s)
        with open(f'{name}-aicut.bat', 'wt') as bat:  # in_file.rsplit('.', 1)[0]
            bat.write(s+'\n')
        with open(f'{name}.json', 'wt') as out:
            out.write(json.dumps(prediction, indent=4, sort_keys=True))
    #shutil.rmtree(name)


if __name__ == "__main__":
    if len(argv) < 2:
        print(f'\nUsage: find_objects.exe video_file_name [sleep_between_requests={sleep_between_requests}]\n')
    else:
        main()
