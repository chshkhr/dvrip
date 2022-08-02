import json
import os
import shutil
import subprocess
from datetime import timedelta
from pathlib import Path
from sys import argv

import requests

serverPort = 5000
serverHost = "localhost"
serverUrl = f"http://{serverHost}:{serverPort}/v1/"
verifySslCert = False
minConfidence = 0.4


def process_dir(directory):
    result_prediction = None
    index = None
    for file_name in os.listdir(directory):
        if file_name.endswith(".jpg"):
            filepath = os.path.join(directory, file_name)
            image_data = open(filepath, "rb").read()

            response = requests.post(
                serverUrl + "vision/detection",
                files={"image": image_data},
                data={"min_confidence": minConfidence},
                verify=verifySslCert
            ).json()

            if response['success']:
                for prediction in response['predictions']:
                    label = prediction['label']
                    if label in ['person', 'car', 'cat', 'dog']:
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
            continue
        else:
            continue
    if result_prediction is not None and index is not None:
        result_prediction['count'] = index
    return result_prediction


def extract_frames(file_name):
    process = subprocess.Popen(['ffmpeg-extract-frames.bat', file_name])
    process.wait()


def main():
    in_file = argv[1]
    print('Extraction started\n')
    extract_frames(in_file)
    name = Path(in_file).stem
    print('AI Image Processing started\n')
    prediction = process_dir(name)
    if prediction is not None:
        print(prediction)
        # x_max = min(prediction['x_max']+10, 2592)
        # y_max = min(prediction['y_max']+10, 1944)
        # x_min = max(prediction['x_min']-10, 0)
        # y_min = max(prediction['y_min']-10, 0)
        y_max = prediction['y_max']
        x_min = prediction['x_min']
        x_max = prediction['x_max']
        y_min = prediction['y_min']
        first = max(int(prediction['first'])-3, 0)
        count = int(prediction['count'])
        last = min(int(prediction['last'])+3,count)
        s = f'ffmpeg.exe -y -i {in_file} -ss 0:{first//60}:{first%60} -t 0:{(last-first)//60}:{(last-first)%60} -filter:v "crop={x_max-x_min}:{y_max-y_min}:{x_min}:{y_min}" -c:a copy {name}-cut.mp4'
        print(s)
        with open(f'{name}-aicut.bat', 'wt') as bat:  # in_file.rsplit('.', 1)[0]
            bat.write(s+'\n')
        with open(f'{name}.json', 'wt') as out:
            out.write(json.dumps(prediction, indent=4, sort_keys=True))
    shutil.rmtree(name)


if __name__ == "__main__":
    if len(argv) < 2:
        print('\nUsage: find_objects.exe video_file_name\n')
    else:
        main()
