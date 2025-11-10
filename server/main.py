import socket
import numpy as np
import threading
import time
import sys
import os

# Abilito supporto ASIO
os.environ['SD_ENABLE_ASIO'] = '1'

import sounddevice as sd

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

# Thread che gestisce il servizio di discovery del server
def discovery_service(udp_sock):
    print(f"[DISCOVERY] In ascolto UDP sulla porta {PORT_DISCOVERY}")
    try:
        while not stop_flag:  # ciclo principale fino a stop_flag
            udp_sock.settimeout(1.0)  # timeout per poter controllare stop_flag
            try:
                data, addr = udp_sock.recvfrom(1024)  # riceve pacchetto UDP
                if data.strip() == b"DISCOVERY":  # se è un pacchetto di discovery
                    # ottiene il proprio IP locale
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as temp:
                        temp.connect(addr)  # connessione temporanea al client
                        local_ip = temp.getsockname()[0]
                    risposta = f"SERVER_IP:{local_ip}".encode()
                    udp_sock.sendto(risposta, addr)  # invia risposta al client
                    print(f"[DISCOVERY] Risposto a {addr} con {local_ip}")
                    with lock:
                        clients.add(addr[0])  # aggiunge l'IP del client alla lista
            except socket.timeout:
                continue  # se scade il timeout, ricomincia il loop
    finally:
        udp_sock.close()  # chiude la socket discovery quando il thread termina

# Thread che gestisce lo streaming audio verso i client
def audio_stream(input_device=None):
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # socket UDP per inviare audio

    # Callback della libreria sounddevice: chiamata per ogni blocco audio catturato
    def callback(indata, frames, time, status):
        if status:  # stampa eventuali warning dello stream
            print(status)
        data_bytes = indata.astype(np.int16).tobytes()  # converte i dati in bytes
        with lock:
            for client_ip in clients:  # invia il pacchetto audio a tutti i client
                udp_sock.sendto(data_bytes, (client_ip, PORT_AUDIO))

    try:
        # apre lo stream di input audio con i parametri specificati
        with sd.InputStream(channels=CHANNELS, samplerate=RATE, blocksize=CHUNK,
                            dtype='int16', device=input_device, callback=callback):
            print(f"[AUDIO] Streaming audio UDP dal dispositivo '{input_device}' in corso...")
            while not stop_flag:  # loop principale fino a stop_flag
                time.sleep(0.1)  # piccolo delay per ridurre l'uso CPU
    finally:
        udp_sock.close()  # chiude la socket quando termina lo streaming

# Punto di partenza del programma
if __name__ == "__main__":
    print("Dispositivi disponibili:")
    print(sd.query_devices())  # mostra tutti i dispositivi audio disponibili

    # socket UDP per il servizio di discovery
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # abilita broadcast
    udp_sock.bind(('0.0.0.0', PORT_DISCOVERY))  # lega alla porta discovery

    # avvia thread per il discovery
    t_discovery = threading.Thread(target=discovery_service, args=(udp_sock,), daemon=True)
    t_discovery.start()

    # socket UDP per inviare audio/terminate ai client
    udp_audio_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        audio_stream(DEVICE)  # avvia lo streaming audio
    except KeyboardInterrupt:  # gestione CTRL+C
        print("\n[SERVER] CTRL+C ricevuto. Invio pacchetto TERMINATE ai client...")
        terminate_msg = b"TERMINATE"  # messaggio speciale per fermare i client
        with lock:
            for client_ip in clients:  # invia TERMINATE a tutti i client connessi
                udp_audio_sock.sendto(terminate_msg, (client_ip, PORT_AUDIO))
    finally:
        stop_flag = True  # ferma i thread
        t_discovery.join()  # attende la terminazione del thread discovery
        udp_audio_sock.close()  # chiude la socket audio
        sys.exit(0)  # termina il programma