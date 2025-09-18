import sounddevice as sd
import socket
import numpy as np

# ----------------- CONFIGURAZIONE -----------------
CHANNELS   = 1          # Numero di canali ricevuti
SAMPLERATE = 48000      # Frequenza di campionamento
BLOCKSIZE  = 1024       # Dimensione del blocco audio
DISCOVERY_PORT = 5000   # Porta su cui il server ascolta il discovery
TCP_PORT   = 5000       # Stessa porta usata poi per la connessione audio
BLACKHOLE_DEVICE = 32

# ----------------- DISCOVERY -----------------
def discover_server():
    """
    Invia un messaggio broadcast DISCOVERY e attende la risposta
    con l'IP del server.
    """
    msg = b"DISCOVERY"
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp.settimeout(3)  # timeout di qualche secondo

    # Invia il pacchetto broadcast
    udp.sendto(msg, ('255.255.255.255', DISCOVERY_PORT))
    print("Inviato pacchetto di discovery...")

    try:
        data, addr = udp.recvfrom(1024)
        print(f"Risposta discovery da {addr}: {data}")
        if data.startswith(b"SERVER_IP:"):
            server_ip = data.decode().split("SERVER_IP:")[1]
            return server_ip.strip()
    except socket.timeout:
        raise RuntimeError("Nessuna risposta di discovery ricevuta.")
    finally:
        udp.close()

# ----------------- CONNESSIONE TCP -----------------
SERVER_IP = discover_server()
print(f"IP del server rilevato: {SERVER_IP}")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((SERVER_IP, TCP_PORT))
print("Connesso al server audio!")

# ----------------- CALLBACK AUDIO -----------------
def audio_callback(outdata, frames, time, status):
    if status:
        print(status)
    try:
        # Ricevo dati dal server
        data = b''
        needed = frames * CHANNELS * 4  # 4 byte per float32
        while len(data) < needed:
            packet = sock.recv(needed - len(data))
            if not packet:
                raise ConnectionError("Server chiuso")
            data += packet

        # Converto in array NumPy
        audio_block = np.frombuffer(data, dtype='float32').reshape(frames, CHANNELS)

        # Copio nei primi canali e azzero i restanti
        outdata[:, :CHANNELS] = audio_block
        if outdata.shape[1] > CHANNELS:
            outdata[:, CHANNELS:] = 0.0

    except Exception as e:
        print("Errore audio:", e)
        outdata.fill(0.0)

# ----------------- STREAM OUTPUT -----------------
with sd.OutputStream(channels=CHANNELS,
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