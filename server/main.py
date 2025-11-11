import socket
import numpy as np
import threading
import time
import sys
import os
import signal
import sounddevice as sd

# Abilito supporto ASIO
os.environ['SD_ENABLE_ASIO'] = '1'

# Porte utilizzate per discovery e streaming audio
PORT_DISCOVERY = 50000
PORT_AUDIO = 50020

# Configurazione dispositivo e parametri audio
DEVICE = 1      # indice del dispositivo di input audio
CHANNELS = 8    # numero di canali audio
RATE = 48000    # sample rate (Hz)
CHUNK = 512     # dimensione blocco audio

clients = set()  # insieme degli IP dei client connessi
lock = threading.Lock()  # lock per gestire accesso concorrente a "clients"
stop_flag = False  # flag globale per fermare i thread

# socket globali
udp_audio_sock = None
t_discovery = None

# Thread che gestisce il servizio di discovery del server
def discovery_service(udp_sock):
    print(f"[DISCOVERY] In ascolto UDP sulla porta {PORT_DISCOVERY}")
    try:
        while not stop_flag:
            udp_sock.settimeout(1.0)
            try:
                data, addr = udp_sock.recvfrom(1024)
                if data.strip() == b"DISCOVERY":
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as temp:
                        temp.connect(addr)
                        local_ip = temp.getsockname()[0]
                    risposta = f"SERVER_IP:{local_ip}".encode()
                    udp_sock.sendto(risposta, addr)
                    print(f"[DISCOVERY] Risposto a {addr} con {local_ip}")
                    with lock:
                        clients.add(addr[0])
            except socket.timeout:
                continue
    finally:
        udp_sock.close()

# Thread che gestisce lo streaming audio verso i client
def audio_stream(input_device=None):
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def callback(indata, frames, time, status):
        if status:
            print(status)
        data_bytes = indata.astype(np.int16).tobytes()
        with lock:
            for client_ip in clients:
                udp_sock.sendto(data_bytes, (client_ip, PORT_AUDIO))

    try:
        with sd.InputStream(channels=CHANNELS, samplerate=RATE, blocksize=CHUNK,
                            dtype='int16', device=input_device, callback=callback):
            print(f"[AUDIO] Streaming audio UDP dal dispositivo '{input_device}' in corso...")
            while not stop_flag:
                time.sleep(0.1)
    finally:
        udp_sock.close()

# Funzione per inviare TERMINATE ai client e chiudere tutto
def graceful_shutdown(*args):
    global stop_flag
    print("\n[SERVER] Arresto in corso... Invio pacchetto TERMINATE ai client.")
    terminate_msg = b"TERMINATE"
    with lock:
        for client_ip in clients:
            try:
                udp_audio_sock.sendto(terminate_msg, (client_ip, PORT_AUDIO))
                print(f"[SERVER] Inviato TERMINATE a {client_ip}")
            except Exception as e:
                print(f"[SERVER] Errore inviando TERMINATE a {client_ip}: {e}")
    stop_flag = True
    if t_discovery and t_discovery.is_alive():
        t_discovery.join()
    if udp_audio_sock:
        udp_audio_sock.close()
    print("[SERVER] Terminato correttamente.")
    sys.exit(0)

# Punto di partenza
if __name__ == "__main__":
    print("Dispositivi disponibili:")
    print(sd.query_devices())

    # socket UDP per il servizio di discovery
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_sock.bind(('0.0.0.0', PORT_DISCOVERY))

    # avvia thread discovery
    t_discovery = threading.Thread(target=discovery_service, args=(udp_sock,), daemon=True)
    t_discovery.start()

    # socket UDP per inviare audio/terminate ai client
    udp_audio_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # registra i signal handler per intercettare tutte le chiusure
    handled_signals = [signal.SIGINT, signal.SIGTERM]
    if hasattr(signal, "SIGHUP"):  # solo su Linux/macOS
        handled_signals.append(signal.SIGHUP)

    for sig in handled_signals:
        signal.signal(sig, graceful_shutdown)

    try:
        audio_stream(DEVICE)
    except Exception as e:
        print(f"[SERVER] Errore: {e}")
        graceful_shutdown()