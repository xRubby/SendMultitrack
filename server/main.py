import sounddevice as sd
import socket
import numpy as np
import queue
import threading

# Configurazione
CHANNELS = 2
SAMPLERATE = 48000
BLOCKSIZE = 1024
SERVER_IP = '0.0.0.0'
PORT = 5000
DEVICE_ID = 62  #ID DEL DISPOSITIVO AUDIO

# Socket TCP
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((SERVER_IP, PORT))
sock.listen(1)
print("In attesa di connessione dal client...")
conn, addr = sock.accept()
print(f"Connessione stabilita con {addr}")

# Coda per buffering audio
audio_queue = queue.Queue(maxsize=10) 

def audio_callback(indata, frames, time, status):
    if status:
        print(status)
    try:
        audio_queue.put_nowait(indata.copy())
    except queue.Full:
        pass

# Thread che invia i blocchi via TCP
def send_thread():
    while True:
        data = audio_queue.get()
        conn.sendall(data.tobytes())

threading.Thread(target=send_thread, daemon=True).start()

with sd.InputStream(device=DEVICE_ID, channels=CHANNELS,
                    samplerate=SAMPLERATE, blocksize=BLOCKSIZE,
                    dtype='float32', callback=audio_callback):
    print("Streaming audio in corso...")
    try:
        while True:
            sd.sleep(1000)
    except KeyboardInterrupt:
        print("Chiusura server...")
        conn.close()
        sock.close()