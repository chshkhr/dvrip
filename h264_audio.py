import os
from sys import argv
from pathlib import Path

from dvrip_download import print_progress_bar, BLK


def extract_audio(in_file):
    audio_fn = os.path.splitext(in_file)[0] + '.audio'
    ln = Path(in_file).stat().st_size // 1024
    suffix = f'Complete of {ln}kb'
    i = 0
    print_progress_bar(i, ln, prefix=in_file, suffix=suffix)
    if i < ln:
        with open(in_file, 'rb') as s, open(audio_fn, 'wb') as audio_out:
            for i in range(ln):
                chunk = s.read(BLK)
                if not chunk:
                    break
                else:
                    end_audio = -1
                    while True:
                        start_audio = chunk.find(b'\x00\x01\xfa\x0e\x02\xa0\x00', end_audio + 1)
                        if start_audio >= 0:
                            start_audio += 7
                            end_audio = start_audio + 160
                            audio_out.write(chunk[start_audio:end_audio])
                        else:
                            break
                    audio_out.flush()
                    if i % 500 == 0:
                        print_progress_bar(i, ln, prefix=in_file, suffix=suffix)
            print_progress_bar(i, i, prefix=in_file, suffix=suffix)
            audio_out.close()
        s.close()


def main():
    extract_audio(argv[1])


if __name__ == "__main__":
    if len(argv) < 2:
        print('\nUsage: h264_audio.exe file_name.h264\n')
    else:
        main()
