# Zender

Simple LAN file-transfer utility using UDP discovery and TCP file transfer.

Summary
-------
`Zender` discovers peers on the local network (UDP broadcast), negotiates a TCP connection, and sends or receives files using a small, interactive console UI and native file/folder choosers.

Key files
---------
- `src/Zender.py` — main implementation (discovery, connection, transfer, console UI).
- `test/test_Zender.py` — interactive test/demo for sending/receiving sockets.

Features
--------
- Peer discovery (broadcast / scan).
- TCP-based file transfer with simple framing (filename length, filename, filesize, then file bytes).
- Console menu for scan/broadcast and send/receive flows.
- Cross-platform input handling (Windows `msvcrt`, Unix `select`) and Tk `filedialog` for choosing files/folders.

Requirements
------------
- Python 3.8+
- Optional: `netifaces` for better broadcast address detection (`pip install netifaces`).
- `tkinter` (usually included with Python on Windows/macOS; install system package on some Linux distributions).

Quickstart
----------
1. (Recommended) Create and activate a virtual environment:

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1   # Windows PowerShell
# or
.\\.venv\\Scripts\\activate.bat   # Windows cmd
source .venv/bin/activate            # Unix/macOS
```

2. (Optional) Install `netifaces`:

```powershell
pip install netifaces
```

3. Run the interactive Zender app:

```powershell
python -m src.Zender
# or
python src/Zender.py
```

Usage notes
-----------
- Main menu: `[1] Scan` to look for nearby devices, `[2] Broadcast` to advertise and accept a connection, `[3] Exit`.
- After connecting, choose `[1] Send files` to open a file dialog and send one or more files, or `[2] Receive files` to pick a destination folder and receive incoming files.
- On the console prompts, press `q` to cancel scans or receives where supported.
- The tool uses a simple framed protocol: command byte (0x01=file), 4-byte filename-length, filename, 4-byte filesize, file bytes.

Testing / Demo
--------------
- The included `test/test_Zender.py` file acts as an interactive demo to create a listening or connecting socket. Run it and follow on-screen prompts:

```powershell
python -m pytest test/test_Zender.py -q
```

Or run two terminals manually:

- Terminal A (listener):
  ```powershell
  python -m src.Zender   # choose Broadcast and accept
  ```
- Terminal B (sender):
  ```powershell
  python -m src.Zender   # choose Scan and connect, then Send files
  ```

Notes & caveats
---------------
- The code falls back to the broadcast address `255.255.255.255` when `netifaces` is not available or no broadcast address is found.
- On Windows, console key detection uses `msvcrt.kbhit()`; on Unix it uses `select` and reading from stdin.
- The UI uses `tkinter.filedialog` for file/folder selection — when running headless or in CI, GUI dialogs will block or fail.
- The current transfer protocol is intentionally simple and meant for local, trusted networks — it has no encryption or integrity verification.

Contributing
------------
PRs and issues welcome. If you add features (e.g., resume, checksums, GUI, encryption), include tests and a short usage example.

License
-------
Provided for learning and experimentation.
