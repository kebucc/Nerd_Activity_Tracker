# Nerd Activity Tracker

Tracker dell'attivita di mouse e tastiera con dashboard web. Monitora **quando** usi mouse e tastiera durante la giornata e visualizza i dati con timeline separate e statistiche riassuntive.

## Requisiti

- Python 3.10+
- Windows

## Installazione

```bash
cd "d:\K-TUF-REPOSITORY\BkLAb\Nerd_Activity_Tracker"
pip install -r requirements.txt
```

## Utilizzo

### 1. Avviare il tracker

Il tracker registra in background i periodi di attivita di mouse e tastiera, salvandoli in un database SQLite locale.

```bash
python tracker.py
```

Una "sessione" e un periodo continuo di attivita. Se l'input resta fermo per **3 secondi**, la sessione viene chiusa e salvata. Sessioni inferiori a 0.5 secondi vengono ignorate.

Mouse e tastiera vengono tracciati separatamente con timeline e statistiche indipendenti.

Per fermarlo: `Ctrl+C`.

### 2. Avviare la dashboard

```bash
python dashboard.py
```

Apri nel browser: **http://127.0.0.1:5000**

La dashboard mostra:

- **Timeline Mouse 24h** — barra orizzontale verde con i periodi di movimento mouse
- **Timeline Tastiera 24h** — barra orizzontale blu con i periodi di digitazione
- **Statistiche per tipo** — tempo totale, numero sessioni e durata media (separati per mouse e tastiera)
- **Tabella dettaglio** — elenco completo con tipo, orario inizio, fine e durata
- **Navigazione date** — frecce per consultare i giorni passati

### 3. Avvio automatico al login (opzionale)

Esegui come **Amministratore**:

```bash
python install_task.py
```

Questo registra il tracker nel Task Scheduler di Windows. Si avviera automaticamente ad ogni login senza finestra visibile.

Per rimuovere l'auto-start:

```bash
python install_task.py --uninstall
```

## Struttura progetto

```
Nerd_Activity_Tracker/
├── config.py           # Configurazione (soglia idle, porta, path DB)
├── db.py               # Layer database SQLite
├── tracker.py          # Daemon tracking mouse + tastiera
├── dashboard.py        # Server Flask
├── install_task.py     # Script auto-start Windows
├── requirements.txt    # Dipendenze (pynput, flask)
├── Avvia Dashboard.bat # Shortcut per avviare la dashboard
├── templates/
│   ├── base.html
│   └── index.html
├── static/
│   ├── style.css
│   └── dashboard.js
└── data/
    └── mouse_activity.db   # Creato automaticamente al primo avvio
```

## Configurazione

Tutti i parametri sono in `config.py`:

| Parametro | Default | Descrizione |
|---|---|---|
| `IDLE_THRESHOLD_SECONDS` | `3` | Secondi di inattivita per chiudere una sessione |
| `MIN_SESSION_DURATION` | `0.5` | Durata minima (in secondi) per salvare una sessione |
| `DASHBOARD_HOST` | `127.0.0.1` | Host del server Flask |
| `DASHBOARD_PORT` | `5000` | Porta del server Flask |

## Database

SQLite con una singola tabella `sessions`:

| Colonna | Tipo | Descrizione |
|---|---|---|
| `session_id` | INTEGER | ID auto-incrementale |
| `type` | TEXT | Tipo di input (`mouse` o `keyboard`) |
| `start_time` | TEXT | Inizio sessione (ISO 8601) |
| `end_time` | TEXT | Fine sessione (ISO 8601) |
| `duration` | REAL | Durata in secondi |

Il database si trova in `data/mouse_activity.db` e viene creato automaticamente. Cresce di circa 10-20 KB al giorno.

## API

La dashboard espone anche endpoint JSON:

| Endpoint | Descrizione |
|---|---|
| `GET /api/sessions/<data>` | Tutte le sessioni per data (es. `2026-02-11`) |
| `GET /api/sessions/<data>?type=mouse` | Solo sessioni mouse |
| `GET /api/sessions/<data>?type=keyboard` | Solo sessioni tastiera |
| `GET /api/summary/<data>` | Statistiche aggregate per data |
| `GET /api/summary/<data>?type=mouse` | Statistiche solo mouse |
| `GET /api/dates` | Elenco date con dati registrati |
