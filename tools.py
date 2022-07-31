def separate_video_and_audio_v2(in_file):

    def reassemble_bin_payload():
        nonlocal h264_in, metadata

        def internal_to_type(data_type, value):
            if data_type == 0x1FC or data_type == 0x1FD:
                if value == 1:
                    return "mpeg4"
                elif value == 2:
                    return "h264"
                elif value == 3:
                    return "h265"
            elif data_type == 0x1F9:
                if value == 1 or value == 6:
                    return "info"
            elif data_type == 0x1FA:
                if value == 0xE:
                    return "g711a"
            elif data_type == 0x1FE and value == 0:
                return "jpeg"
            return None

        def internal_to_datetime(value):
            second = value & 0x3F
            minute = (value & 0xFC0) >> 6
            hour = (value & 0x1F000) >> 12
            day = (value & 0x3E0000) >> 17
            month = (value & 0x3C00000) >> 22
            year = ((value & 0xFC000000) >> 26) + 2000
            return datetime(year, month, day, hour, minute, second)

        length = 0
        buf = bytearray()
        # start_time = time.time()

        while True:
            data = h264_in.read(20)
            (
                head,
                version,
                session,
                sequence_number,
                total,
                cur,
                msgid,
                len_data,
            ) = struct.unpack("BB2xIIBBHI", data)
            packet = h264_in.read(len_data)
            frame_len = 0
            if length == 0:
                media = None
                frame_len = 8
                (data_type,) = struct.unpack(">I", packet[:4])
                if data_type == 0x1FC or data_type == 0x1FE:
                    frame_len = 16
                    (media, metadata["fps"], w, h, dt, length,) = struct.unpack(
                        "BBBBII", packet[4:frame_len]
                    )
                    metadata["width"] = w * 8
                    metadata["height"] = h * 8
                    metadata["datetime"] = internal_to_datetime(dt)
                    if data_type == 0x1FC:
                        metadata["frame"] = "I"
                elif data_type == 0x1FD:
                    (length,) = struct.unpack("I", packet[4:frame_len])
                    metadata["frame"] = "P"
                elif data_type == 0x1FA:
                    (media, samp_rate, length) = struct.unpack(
                        "BBH", packet[4:frame_len]
                    )
                elif data_type == 0x1F9:
                    (media, n, length) = struct.unpack("BBH", packet[4:frame_len])
                # special case of JPEG shapshots
                elif data_type == 0xFFD8FFE0:
                    return packet
                else:
                    raise ValueError(data_type)
                if media is not None:
                    metadata["type"] = internal_to_type(data_type, media)
            buf.extend(packet[frame_len:])
            length -= len(packet) - frame_len
            if length == 0:
                return buf
            # elapsed_time = time.time() - start_time
            # if elapsed_time > timeout:
            #     return None