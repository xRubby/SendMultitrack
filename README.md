# 🎵 SendMultitrack

Stream audio **multi-canale** in tempo reale su rete locale tramite UDP.  
Supporta più client, discovery automatico del server e terminazione sicura.

## ⚡ Features

- Streaming audio senza limiti di canali (configurabile)
- Discovery automatico del server in LAN
- Supporto dispositivi ASIO su Windows
- Terminazione sicura con pacchetto `TERMINATE`
- Configurabile: dispositivo, numero di canali, sample rate

## ⚙️ Configurazione

Modifica i parametri in **server.py** e **client.py**:

```python
DEVICE = 1       # Indice dispositivo di input (server) o nome dispositivo output (client)
CHANNELS = 8     # Numero di canali audio
RATE = 48000     # Sample rate (Hz)
CHUNK = 512      # Dimensione blocco audio
```

## 🚀 Avvio

### Avvio del Server

Controlla i dispositivi audio disponibili e avvia lo streaming audio:

```bash
python server.py
```

Il server inizierà a rispondere ai pacchetti di discovery dei client e invierà l’audio UDP.

### Avvio del Client

1. Controlla i dispositivi audio disponibili e avvia il client:

```bash
python client.py
```

Il client cercherà automaticamente il server in rete locale e riprodurrà l’audio ricevuto.

## ⚠️ Note

- Assicurati che le porte UDP **50000** (discovery) e **50020** (audio) siano aperte sulla rete e non bloccate da firewall.
- La qualità dell’audio dipende dalla rete locale e dalle prestazioni del dispositivo audio.
- Su Windows, per usare ASIO, la variabile `SD_ENABLE_ASIO` è già impostata nel server (`os.environ['SD_ENABLE_ASIO'] = '1'`).
- Tutti i parametri audio sono modificabili: dispositivo, numero di canali, sample rate, dimensione blocco.
