Windows (Command Prompt):
    py -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt

    To run:
    venv\Scripts\activate
    py app.py

Linux/MacOS?:
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

    To run:
    source .venv/bin/activate
    python3 app.py

You can also try using the following files to start the application, but only the Linux version is tested:
Windows: eos-explorer.bat
MacOS: eos-explorer.command
Linux: eos-explorer.desktop
