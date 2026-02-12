# Versione Distribuibile — Installer Windows

## Contesto

Creare un installer Windows (.exe) per distribuire l'applicazione Nerd Activity Tracker senza richiedere Python installato. I dati (database, settings) vengono salvati accanto all'eseguibile.

**Strumenti:** PyInstaller (freeze → exe) + Inno Setup (packaging → installer)

---

## Problemi da risolvere

### 1. Path resolution in modalità frozen
`config.py:4` usa `os.path.dirname(os.path.abspath(__file__))` per `BASE_DIR`. Con PyInstaller, `__file__` punta dentro il bundle, non accanto all'exe. Serve distinguere:
- `BASE_DIR` → accanto all'exe (per `data/`, `settings.json`)
- `BUNDLE_DIR` → dentro il bundle, `sys._MEIPASS` (per `templates/`, `static/`)

### 2. Dashboard subprocess non funziona da frozen
`tracker.py:68-89` lancia `dashboard.py` come subprocess con `pythonw`. Da exe, `sys.executable` è l'exe stesso e `dashboard.py` non esiste come file. Soluzione: Flask in daemon thread quando frozen.

### 3. Flask non trova templates/static
`dashboard.py:10` crea `Flask(__name__)` che cerca `templates/` e `static/` relativi al modulo. Da frozen servono path espliciti verso `BUNDLE_DIR`.

### 4. install_task.py assume Python interpreter
`install_task.py:8-9` usa `sys.executable.replace("python.exe", "pythonw.exe")`. Da frozen, l'exe va lanciato direttamente.

### 5. Nessuna icona .ico
L'app genera l'icona tray con Pillow ma non ha un file `.ico` per l'exe e l'installer.

---

## Piano di implementazione

### Step 1: Modificare `config.py`
Aggiungere `import sys` e frozen detection:
```python
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = BASE_DIR
```
Tutto il resto del file resta invariato. Quando non frozen, `BASE_DIR == BUNDLE_DIR` → retrocompatibile.

### Step 2: Modificare `dashboard.py`
- Aggiungere `import os` agli import
- Passare path espliciti a Flask:
```python
app = Flask(__name__,
    template_folder=os.path.join(config.BUNDLE_DIR, 'templates'),
    static_folder=os.path.join(config.BUNDLE_DIR, 'static'))
```
- Aggiungere funzione `run_dashboard()` per lancio da thread:
```python
def run_dashboard():
    db.init_db()
    app.run(host=DASHBOARD_HOST, port=DASHBOARD_PORT, debug=False, use_reloader=False)
```
`use_reloader=False` è critico — il reloader di Flask spawna un processo figlio che crasherebbe da frozen.

### Step 3: Modificare `tracker.py`
Sostituire `open_dashboard()` con logica dual-mode:
- **Frozen:** importa `dashboard.run_dashboard` e lo lancia in daemon thread
- **Non frozen:** mantiene il comportamento attuale (subprocess con pythonw)

La funzione `on_exit()` non richiede modifiche — il thread daemon muore automaticamente con il processo.

### Step 4: Modificare `install_task.py`
Quando frozen, usare `sys.executable` direttamente come comando del task scheduler invece di `pythonw + script`.

### Step 5: Creare `NerdActivityTracker.spec` (nuovo)
Spec file PyInstaller:
- Entry point: `tracker.py`
- Modo `--onedir` (startup veloce, Flask funziona senza problemi)
- `--windowed` (nessuna console)
- `--add-data` per `templates/` e `static/`
- `hiddenimports`: `dashboard`, `pynput.mouse._win32`, `pynput.keyboard._win32`, moduli Flask/Jinja2
- Icona: `assets/app.ico`

### Step 6: Creare `installer.iss` (nuovo)
Script Inno Setup:
- Installa in `{autopf}\Nerd Activity Tracker` (per-utente, no admin)
- Collegamento nel Menu Start
- Checkbox opzionale: icona desktop
- Checkbox opzionale: avvio automatico con Windows (via registro `HKCU\...\Run`)
- Uninstaller che rimuove la chiave di registro
- I dati utente (`data/`) NON vengono cancellati alla disinstallazione

### Step 7: Creare `build.py` (nuovo)
Script di build automation:
1. Genera `assets/app.ico` con Pillow (multi-size: 16, 32, 48, 256px) — design: cerchio verde + cerchio blu come l'icona tray
2. Esegue PyInstaller con lo spec file
3. Con flag `--installer`: esegue anche Inno Setup

Uso: `python build.py` oppure `python build.py --installer`

### Step 8: Creare `requirements-build.txt` (nuovo)
```
-r requirements.txt
pyinstaller>=6.0
```

### Step 9: Aggiornare `.gitignore`
Aggiungere: `build/`, `dist/`, `installer_output/`, `assets/app.ico`

### Step 10: Aggiornare `CLAUDE.md` con sezione Building

---

## Struttura output finale

```
dist/NerdActivityTracker/
  NerdActivityTracker.exe
  _internal/               ← Python runtime + templates/ + static/
  data/                    ← creata al primo avvio (DB + settings)

installer_output/
  NerdActivityTrackerSetup.exe   ← installer per l'utente finale
```

## Verifica

1. `python build.py` → verifica che `dist/NerdActivityTracker/NerdActivityTracker.exe` esista
2. Lanciare l'exe → l'icona tray deve apparire
3. Click su "Open Dashboard" → Flask parte, browser si apre su `127.0.0.1:5000`
4. Verificare che il tracking mouse/keyboard funzioni e i dati appaiano nella dashboard
5. Chiudere e rilanciare → i dati devono persistere in `data/data.db`
6. `python build.py --installer` → verifica che `NerdActivityTrackerSetup.exe` venga creato
7. Eseguire l'installer → l'app si installa, collegamento nel Menu Start funziona
