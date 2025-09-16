import sounddevice as sd
import socket
import struct
import numpy as np

# Configurazione
CHANNELS = 2
SAMPLERATE = 48000
BLOCKSIZE = 1024
SERVER_IP = '0.0.0.0'
PORT = 5000

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

with sd.InputStream(device=62, channels=CHANNELS, samplerate=SAMPLERATE,
                    blocksize=BLOCKSIZE, dtype='float32', callback=callback):
    print("Streaming audio in corso...")
    try:
        while True:
            sd.sleep(1000)
    except KeyboardInterrupt:
        print("Chiusura server...")
        conn.close()
        sock.close()