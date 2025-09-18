import os
import socket
import threading
import numpy as np
import sounddevice as sd

# ---------------------------------------------------
# CONFIGURAZIONE
# ---------------------------------------------------
os.environ['SD_ENABLE_ASIO'] = '1'   # Abilito supporto ASIO

CHANNELS    = 2
SAMPLERATE  = 48000
BLOCKSIZE   = 1024
SERVER_IP   = '0.0.0.0'   # TCP bind
PORT        = 5000        # stessa porta sia per TCP che per UDP discovery
DEVICE_NAME = 62

# ---------------------------------------------------
# FUNZIONE DISCOVERY
# ---------------------------------------------------
def discovery_service():
    """
    Ascolta i pacchetti UDP DISCOVERY e risponde con l'IP locale
    usato verso il client.
    """
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_sock.bind(('0.0.0.0', PORT))
    print(f"[DISCOVERY] In ascolto UDP sulla porta {PORT}")

    while True:
        data, addr = udp_sock.recvfrom(1024)
        if data.strip() == b"DISCOVERY":
            # Calcola l'IP locale che il server userebbe verso quel client
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as temp:
                temp.connect(addr)
                local_ip = temp.getsockname()[0]

            risposta = f"SERVER_IP:{local_ip}".encode()
            udp_sock.sendto(risposta, addr)
            print(f"[DISCOVERY] Risposto a {addr} con {local_ip}")

# Avvia il thread del discovery
threading.Thread(target=discovery_service, daemon=True).start()

# ---------------------------------------------------
# TCP STREAMING AUDIO
# ---------------------------------------------------
print(sd.query_devices())

tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_sock.bind((SERVER_IP, PORT))
tcp_sock.listen(1)
print("In attesa di connessione TCP dal client...")
conn, addr = tcp_sock.accept()
print(f"Connessione TCP stabilita con {addr}")

def callback(indata, frames, time, status):
    if status:
        print(status)
    # invio blocchi audio
    try:
        conn.sendall(indata.tobytes())
    except BrokenPipeError:
        print("Connessione TCP interrotta")
        raise KeyboardInterrupt

with sd.InputStream(device=DEVICE_NAME,
                    channels=CHANNELS,
                    samplerate=SAMPLERATE,
                    blocksize=BLOCKSIZE,
                    dtype='float32',
                    callback=callback):
    print("Streaming audio in corso...")
    try:
        while True:
            sd.sleep(1000)
    except KeyboardInterrupt:
        print("Chiusura server...")
        conn.close()
        tcp_sock.close()