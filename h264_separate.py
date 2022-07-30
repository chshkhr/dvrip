import os
from sys import argv


PATTERN = b'\x00\x01\xfa\x0e\x02\xa0\x00'


def separate_video_and_audio(in_file):
    audio_fn = os.path.splitext(in_file)[0] + '.audio'
    video_fn = os.path.splitext(in_file)[0] + '.video'
    with open(in_file, 'rb') as h264_in,\
            open(audio_fn, 'wb') as audio_out, \
            open(video_fn, 'wb') as video_out:
        data = h264_in.read()
        end_audio = -1
        start_audio = data.find(PATTERN, end_audio + 1)
        if start_audio < 0:
            video_out.write(data)
        else:
            video_out.write(data[:start_audio])
            while start_audio >= 0:
                while data[start_audio:start_audio+7] == PATTERN:
                    start_audio += 7
                    end_audio = start_audio + 160
                    audio_out.write(data[start_audio:end_audio])
                    start_audio = end_audio + 1
                start_audio = data.find(PATTERN, end_audio + 1)
                if start_audio > 0:
                    video_out.write(data[end_audio+1:start_audio-1])
            video_out.write(data[end_audio+1:])


def main():
    separate_video_and_audio(argv[1])


if __name__ == "__main__":
    if len(argv) < 2:
        print('\nUsage: h264_separate.exe file_name.h264\n')
    else:
        main()
