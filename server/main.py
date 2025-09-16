import os

# Abilito supporto ASIO
os.environ['SD_ENABLE_ASIO'] = '1'

import socket
import struct
import numpy as np
import sounddevice as sd

# Configurazione
CHANNELS = 40
SAMPLERATE = 48000
BLOCKSIZE = 1024
SERVER_IP = '0.0.0.0'
PORT = 5000
DEVICE_NAME = "REAC:"

print(sd.query_devices()) 

# Socket TCP
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((SERVER_IP, PORT))
sock.listen(1)
print("In attesa di connessione dal client...")
conn, addr = sock.accept()
print(f"Connessione stabilita con {addr}")

# Callback audio
def callback(indata, frames, time, status):
    if status:
        print(status)
    # Converti in bytes e invia
    conn.sendall(indata.tobytes())

with sd.InputStream(device=DEVICE_NAME, channels=CHANNELS, samplerate=SAMPLERATE,
                    blocksize=BLOCKSIZE, dtype='float32', callback=callback):
    print("Streaming audio in corso...")
    try:
        while True:
            sd.sleep(1000)
    except KeyboardInterrupt:
        print("Chiusura server...")
        conn.close()
        sock.close()