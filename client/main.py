import socket
import sounddevice as sd
import numpy as np
import threading
import sys
import time

# Porte utilizzate per discovery del server e streaming audio
PORT_DISCOVERY = 50000
PORT_AUDIO = 50020

# Configurazione dispositivo e parametri audio
DEVICE = "BlackHole 64ch"  # nome del dispositivo audio di output
CHANNELS = 8               # numero di canali audio
RATE = 48000               # sample rate (Hz)
CHUNK = 512                # dimensione del blocco audio da ricevere

# Flag globale per fermare il client audio
stop_flag = False

# Funzione per scoprire il server in rete locale tramite broadcast UDP
def discover_server():
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # crea socket UDP
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # abilita broadcast
    udp_sock.settimeout(3)  # timeout 3 secondi
    udp_sock.sendto(b"DISCOVERY", ('<broadcast>', PORT_DISCOVERY))  # invia messaggio di discovery
    
    try:
        # attende risposta dal server
        data, addr = udp_sock.recvfrom(1024)
        ip = data.decode().split(':')[1]  # estrae l'IP dalla risposta
        print(f"[DISCOVERY] Server trovato: {ip}")
        return ip
    except socket.timeout:
        print("[DISCOVERY] Server non trovato")
        return None
    finally:
        udp_sock.close()  # chiude la socket

# Funzione client audio che riceve pacchetti audio UDP e li riproduce
def audio_client(server_ip, output_device=None):
    global stop_flag
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # crea socket UDP
    udp_sock.bind(('', PORT_AUDIO))  # lega la socket alla porta per ricevere audio
    print(f"[AUDIO] In ascolto UDP sulla porta {PORT_AUDIO}")

    # Callback della libreria sounddevice: viene chiamata per ogni blocco audio
    def callback(outdata, frames, time, status):
        global stop_flag
        if status:  # stampa eventuali warning dello stream
            print(status)
        try:
            # riceve un pacchetto UDP (CHUNK * CHANNELS * 2 bytes + header)
            data, _ = udp_sock.recvfrom(CHUNK * CHANNELS * 2 + 20)
            
            if data == b"TERMINATE":  # messaggio speciale per terminare il client
                print("\n[AUDIO] Pacchetto TERMINATE ricevuto dal server. Chiudo client.")
                stop_flag = True
                raise sd.CallbackStop()  # ferma lo stream audio
            
            # converte i dati in array NumPy e li rimodella secondo i canali
            audio = np.frombuffer(data, dtype=np.int16).reshape(-1, CHANNELS)
            outdata[:] = audio  # invia i dati allo stream audio
        except sd.CallbackStop:
            raise  # rilancia per fermare lo stream
        except:
            outdata.fill(0)  # in caso di errore, invia silenzio

    try:
        # apre lo stream di output audio con i parametri specificati
        with sd.OutputStream(channels=CHANNELS, samplerate=RATE, blocksize=CHUNK,
                             dtype='int16', device=output_device, callback=callback):
            while not stop_flag:  # loop principale fino alla fine
                time.sleep(0.05)  # piccolo delay per ridurre uso CPU
    except KeyboardInterrupt:
        print("\n[AUDIO] CTRL+C ricevuto. Terminazione client.")
    finally:
        udp_sock.close()  # chiude la socket
        print("[AUDIO] Client terminato.")
        sys.exit(0)  # termina il programma

# Punto di partenza del programma
if __name__ == "__main__":
    print("Dispositivi disponibili:")
    print(sd.query_devices())  # mostra tutti i dispositivi audio disponibili

    print("Selezionato dispositivo di output audio:", DEVICE)

    server_ip = discover_server()  # cerca il server in rete
    if server_ip:
        audio_client(server_ip, DEVICE)  # avvia il client audio