import sounddevice as sd
import socket
import numpy as np

# ----------------- CONFIGURAZIONE -----------------
CHANNELS = 2            # Numero di canali ricevuti
SAMPLERATE = 48000       # Frequenza di campionamento
BLOCKSIZE = 1024         # Dimensione del blocco audio
SERVER_IP = '192.168.1.113'  # Inserisci l'IP del server Windows
PORT = 5000

# Nome del dispositivo BlackHole 64ch (come appare in sd.query_devices())
BLACKHOLE_DEVICE = 'BlackHole 64ch'

# ----------------- CONNESSIONE TCP -----------------
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((SERVER_IP, PORT))
print("Connesso al server!")

# ----------------- CALLBACK AUDIO -----------------
def audio_callback(outdata, frames, time, status):
    if status:
        print(status)
    try:
        # Ricevo dati dal server
        data = b''
        while len(data) < frames * CHANNELS * 4:  # 4 byte per float32
            packet = sock.recv(frames * CHANNELS * 4 - len(data))
            if not packet:
                raise ConnectionError("Server chiuso")
            data += packet

        # Converto in array NumPy
        audio_block = np.frombuffer(data, dtype='float32')
        audio_block = audio_block.reshape(frames, CHANNELS)

        # BlackHole ha più canali (64), metto i 40 canali ricevuti nei primi 40
        outdata[:, :CHANNELS] = audio_block
        # Gli altri canali li azzero
        if outdata.shape[1] > CHANNELS:
            outdata[:, CHANNELS:] = 0.0

    except Exception as e:
        print("Errore audio:", e)
        outdata.fill(0.0)

# ----------------- STREAM OUTPUT -----------------
with sd.OutputStream(channels=64,  # BlackHole 64ch
                     samplerate=SAMPLERATE,
                     blocksize=BLOCKSIZE,
                     dtype='float32',
                     device=BLACKHOLE_DEVICE,
                     callback=audio_callback):
    print("Riproduzione in corso su BlackHole 64ch...")
    try:
        while True:
            sd.sleep(1000)
    except KeyboardInterrupt:
        print("Chiusura client...")
        sock.close()