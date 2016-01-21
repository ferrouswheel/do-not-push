from sys import byteorder
from array import array
from struct import pack

import os
import pyaudio
import wave
import subprocess

THRESHOLD = 500
CHUNK_SIZE = 1024 * 8
FORMAT = pyaudio.paInt16
RATE = 44100

def is_silent(snd_data):
    "Returns 'True' if below the 'silent' threshold"
    return max(snd_data) < THRESHOLD

def normalize(snd_data):
    "Average the volume out"
    MAXIMUM = 16384
    times = float(MAXIMUM)/max(abs(i) for i in snd_data)

    r = array('h')
    for i in snd_data:
        r.append(int(i*times))
    return r

def trim(snd_data):
    "Trim the blank spots at the start and end"
    def _trim(snd_data):
        snd_started = False
        r = array('h')

        for index, i in enumerate(snd_data):
            if not snd_started and abs(i)>THRESHOLD:
                snd_started = True
                j = index - 1024
                if j < 0: j = 0
                r.extend(snd_data[j:index])

            elif snd_started:
                r.append(i)
        return r

    # Trim to the left
    snd_data = _trim(snd_data)

    # Trim to the right
    snd_data.reverse()
    snd_data = _trim(snd_data)
    snd_data.reverse()
    return snd_data

def add_silence(snd_data, seconds):
    "Add silence to the start and end of 'snd_data' of length 'seconds' (float)"
    r = array('h', [0 for i in xrange(int(seconds*RATE))])
    r.extend(snd_data)
    r.extend([0 for i in xrange(int(seconds*RATE))])
    return r

def record():
    """
    Record a word or words from the microphone and 
    return the data as an array of signed shorts.

    Normalizes the audio, trims silence from the 
    start and end, and pads with 0.5 seconds of 
    blank sound to make sure VLC et al can play 
    it without getting chopped off.
    """
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT, channels=1, rate=RATE,
        input=True, output=True,
        frames_per_buffer=CHUNK_SIZE)

    num_silent = 0
    snd_started = False

    r = array('h')

    while 1:
        # little endian, signed short
        snd_data = array('h', stream.read(CHUNK_SIZE))
        if byteorder == 'big':
            snd_data.byteswap()
        r.extend(snd_data)

        silent = is_silent(snd_data)

        if silent and snd_started:
            num_silent += 1
        elif not silent and not snd_started:
            snd_started = True

        if snd_started and num_silent > 5:
            break

    sample_width = p.get_sample_size(FORMAT)
    stream.stop_stream()
    stream.close()
    p.terminate()

    r = normalize(r)
    r = trim(r)
    r = add_silence(r, 0.5)
    return sample_width, r

def save_to_file(path, sample_width, data):
    "outputs the data to wavefile at 'path'"
    data = pack('<' + ('h'*len(data)), *data)

    wf = wave.open(path, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(sample_width)
    wf.setframerate(RATE)
    wf.writeframes(data)
    wf.close()

def play_file(path):
    (root, ext) = os.path.splitext(path)
    if ext == '.wav':
        play_wav(path)
    elif ext == '.mp3':
        play_mp3(path)
    else:
        raise ValueError("Unknown extension %s" % ext)

def play_mp3(path):
    from pydub import AudioSegment
    
    use_pyaudio = False
    if use_pyaudio:
        song = AudioSegment.from_mp3(path)

        print "song rate", song.frame_rate
        print "channels", song.channels
        print "sample format", song.sample_width

        p = pyaudio.PyAudio()
        # Learn what your OS+Hardware can do
        defaultCapability = p.get_default_host_api_info()
        print "default capability", defaultCapability

        # See if you can make it do what you want
        isSupported = p.is_format_supported(output_format=pyaudio.paInt8, output_channels=1, rate=22050, output_device=0)
        print "supported?", isSupported
        isSupported = p.is_format_supported(output_format=p.get_format_from_width(song.sample_width), output_channels=song.channels, rate=song.frame_rate, output_device=0)
        print "supported?", isSupported

        stream = p.open(format=p.get_format_from_width(song.sample_width),
                        channels=song.channels,
                        rate=song.frame_rate,
                        output=True)

        for i in range(0, len(song._data) / CHUNK_SIZE):
            frames = song._data[i*CHUNK_SIZE:(i+1) * CHUNK_SIZE]
            stream.write(frames)

        stream.stop_stream()
        stream.close()

        p.terminate()
    else:
        subprocess.call(['mpg123', '-q', path])


def play_wav(path):
    wf = wave.open(path, 'rb')

    p = pyaudio.PyAudio()

    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True)

    data = wf.readframes(CHUNK_SIZE)

    while data != '':
        stream.write(data)
        data = wf.readframes(CHUNK_SIZE)

    stream.stop_stream()
    stream.close()

    p.terminate()
    wf.close()


def play_back(data, sample_width):
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT, channels=1, rate=RATE,
        output=True,
        frames_per_buffer=CHUNK_SIZE)

    d = data.tostring()
    for i in range(0, len(d) / CHUNK_SIZE):
        frames = d[i*CHUNK_SIZE:(i+1) * CHUNK_SIZE]
        stream.write(frames)

    stream.stop_stream()
    stream.close()

    p.terminate()


if __name__ == '__main__':
    print("play mp3")
    play_file('../data/elevators-000-you-know-there-are-o.mp3')

    print("please speak a word into the microphone")
    sample_width, data = record()
    print ("playing back")
    play_back(data, sample_width)
    print ("saving")
    save_to_file('demo.wav', sample_width, data)
    print("playback...")
    play_file('demo.wav')

