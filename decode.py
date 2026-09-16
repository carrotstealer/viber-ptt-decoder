#!/usr/bin/env python3
"""
    Decode Viber PTT voice files (Speex NB container) to WAV.
    Format: flat stream of records: [optional 0x1a marker][len16le][Speex NB frame].
    Frame sizes match Speex NB CBR qualities: 6/10/15/20/28/38/46 bytes.
"""
import argparse
import ctypes
import struct
import sys
import wave

class SpeexBits(ctypes.Structure):
    _fields_ = [("chars", ctypes.c_char_p), ("nbBits", ctypes.c_int), ("charPtr", ctypes.c_int),
                ("bitPtr", ctypes.c_int), ("owner", ctypes.c_int), ("overflow", ctypes.c_int),
                ("buf_size", ctypes.c_int), ("reserved1", ctypes.c_int), ("reserved2", ctypes.c_void_p)]

class SpeexMode(ctypes.Structure):
    _fields_ = [("mode", ctypes.c_void_p), ("query", ctypes.c_void_p), ("modeName", ctypes.c_char_p),
                ("modeID", ctypes.c_int), ("bitstream_version", ctypes.c_int),
                ("enc_init", ctypes.c_void_p), ("enc_destroy", ctypes.c_void_p), ("enc", ctypes.c_void_p),
                ("dec_init", ctypes.c_void_p), ("dec_destroy", ctypes.c_void_p), ("dec", ctypes.c_void_p),
                ("enc_ctl", ctypes.c_void_p), ("dec_ctl", ctypes.c_void_p)]

SPEEX_SET_SAMPLING_RATE = 24
SPEEX_GET_FRAME_SIZE = 3

def parse(path):
    data = open(path, "rb").read()
    off = 0
    records = []
    while off + 2 <= len(data):
        first = data[off]
        if first == 0x1a and off + 3 <= len(data):
            length = struct.unpack("<H", data[off + 1:off + 3])[0]
            payload_off = off + 3
        else:
            if off + 2 > len(data):
                break
            length = struct.unpack("<H", data[off:off + 2])[0]
            payload_off = off + 2
        if length == 0 or payload_off + length > len(data):
            off += 1
            continue
        records.append(data[payload_off:payload_off + length])
        off = payload_off + length
    return records

def decode(pcm_frames, lib_path=None):
    if lib_path is None:
        lib_path = ("libspeex-1.dll" if sys.platform == "win32"
                    else "libspeex.so.1")
    lib = ctypes.CDLL(lib_path)
    lib.speex_bits_init.argtypes = [ctypes.POINTER(SpeexBits)]
    lib.speex_bits_destroy.argtypes = [ctypes.POINTER(SpeexBits)]
    lib.speex_bits_read_from.argtypes = [ctypes.POINTER(SpeexBits), ctypes.c_char_p, ctypes.c_int]
    lib.speex_decoder_init.restype = ctypes.c_void_p
    lib.speex_decoder_init.argtypes = [ctypes.POINTER(SpeexMode)]
    lib.speex_decoder_destroy.argtypes = [ctypes.c_void_p]
    lib.speex_decoder_ctl.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    lib.speex_decode_int.argtypes = [ctypes.c_void_p, ctypes.POINTER(SpeexBits), ctypes.POINTER(ctypes.c_short)]
    lib.speex_decode_int.restype = ctypes.c_int

    lib.speex_lib_get_mode.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    lib.speex_lib_get_mode.restype = ctypes.POINTER(SpeexMode)
    mode = lib.speex_lib_get_mode(0, None)
    dec = lib.speex_decoder_init(mode)
    lib.speex_decoder_ctl(dec, SPEEX_SET_SAMPLING_RATE, ctypes.byref(ctypes.c_int(8000)))
    framesize = ctypes.c_int(0)
    lib.speex_decoder_ctl(dec, SPEEX_GET_FRAME_SIZE, ctypes.byref(framesize))
    framesize = framesize.value

    bits = SpeexBits()
    lib.speex_bits_init(ctypes.byref(bits))
    out = ctypes.create_string_buffer(2 * framesize)
    pcm = bytearray()
    errors = 0
    for frame in pcm_frames:
        lib.speex_bits_read_from(ctypes.byref(bits), frame, len(frame))
        rc = lib.speex_decode_int(
            dec, ctypes.byref(bits), ctypes.cast(out, ctypes.POINTER(ctypes.c_short)))
        if rc:
            errors += 1
        pcm += out.raw
    lib.speex_decoder_destroy(dec)
    lib.speex_bits_destroy(ctypes.byref(bits))
    return bytes(pcm), errors

def main():
    parser = argparse.ArgumentParser(description="Decode Viber PTT voice files to WAV")
    parser.add_argument("files", nargs="+", help="PTT file(s) to decode")
    parser.add_argument("--libspeex", metavar="PATH", default=None,
                        help="path to the Speex shared library (overrides the default libspeex.so.1 / libspeex-1.dll)")
    args = parser.parse_args()

    for path in args.files:
        records = parse(path)
        pcm, errors = decode(records, args.libspeex)
        if errors > 0:
            print(f"WARNING: {errors} decode error occured, possibly corrupted input file")
        wav_path = path + ".wav"
        with wave.open(wav_path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            w.writeframes(pcm)

if __name__ == "__main__":
    main()