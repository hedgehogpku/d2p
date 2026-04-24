def extract_audio_auto(input_file: str):
    with open(input_file, "rb") as f:
        data = f.read()

    total_len = len(data)
    print(f"📄 文件总长度：{total_len} 字节")
    print("=" * 70)

    # 支持的音频头
    AUDIO_HEADERS = [
        b"ID3",    # MP3
        b"OggS",   # OGG / OPUS
        b"RIFF",   # WAV
        b"fLaC",   # FLAC
        b"\xFF\xFB", b"\xFF\xF3", b"\xFF\xF2"  # 裸MP3
    ]

    audio_offset = -1
    found_header = None
    for header in AUDIO_HEADERS:
        pos = data.find(header)
        if pos != -1 and (audio_offset == -1 or pos < audio_offset):
            audio_offset = pos
            found_header = header

    if audio_offset == -1:
        print("❌ 未找到音频头")
        return None, None

    print(f"✅ 找到音频头：{found_header}")
    print(f"✅ 音频偏移：{audio_offset}")

    # 音频前4字节为长度
    len_bytes = data[audio_offset - 4 : audio_offset]
    print(f"✅ 长度4字节HEX：{len_bytes.hex()}")

    audio_len_big    = int.from_bytes(len_bytes, byteorder="big", signed=False)
    audio_len_little = int.from_bytes(len_bytes, byteorder="little", signed=False)

    print(f"🔍 大端长度：{audio_len_big}")
    print(f"🔍 小端长度：{audio_len_little}")
    print("=" * 70)

    # 自动选合法长度
    if audio_offset + audio_len_little <= total_len:
        audio_length = audio_len_little
        print("✅ 使用小端序")
    else:
        audio_length = audio_len_big
        print("✅ 使用大端序")

    print(f"🎯 最终音频长度：{audio_length}")

    # 分段
    audio_start = audio_offset
    audio_end   = audio_start + audio_length

    before_audio = data[:audio_start]
    audio_data   = data[audio_start:audio_end]
    after_audio  = data[audio_end:]
        
    print(f"📊 三段数据长度:")
    print(f"   音频前: {len(before_audio)} 字节")
    print(f"   音频: {len(audio_data)} 字节")
    print(f"   音频后: {len(after_audio)} 字节")
    if len(after_audio) >= 4:
        print(f"📊 音频后数据开头 HEX: {after_audio[:16].hex().upper()}")
    else:
        print(f"❌ 音频后数据不足4字节: {len(after_audio)} 字节")
    return before_audio,audio_data,after_audio
