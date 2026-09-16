# Viber PTT Decoder

Reverse-engineered decoder for an old versions of Viber Desktop PTT (push-to-talk) voice message files.
Tested messages recorded with Viber Desktop 5.x and 6.x.

## File format

A flat stream of records:

```
[optional 0x1a marker][len16le][Speex NB frame]
```

- Each record is a complete Speex narrowband (8 kHz) frame, up to one copy.
- `len16le` is the little-endian frame length.
- An optional leading `0x1a` byte precedes the length for some records.

## Codec

**Speex NB** (narrowband, 8 kHz, 20 ms frames, 160 samples/frame).

Submode/quality is self-describing in the frame size (CBR):

| Record size | Speex quality |
|-------------|---------------|
| 6 B         | q0            |
| 10 B        | q1            |
| 15 B        | q2            |
| 20 B        | q3            |
| 28 B        | q5            |
| 38 B        | q7            |
| 46 B        | q9            |

The first byte of each record is the Speex mode/submode header byte.

## Usage

```sh
python3 decode.py your_ptt_file
```

Writes `your_ptt_file.wav` (8 kHz mono s16le).

Requires the Speex shared library and Python 3. On Linux this is `libspeex.so.1`; on Windows place `libspeex-1.dll` in `PATH` or the current directory.
