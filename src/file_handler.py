import psutil
import time
import ctypes
import subprocess
import os
import json
from pathlib import Path

CONFIG_FILE = "eldenring_config.json"
COMMON_PATHS = [
    r"C:\Program Files (x86)\Steam\steamapps\common\ELDEN RING\Game",
    r"C:\Program Files\Steam\steamapps\common\ELDEN RING\Game",
    r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game",
    r"E:\SteamLibrary\steamapps\common\ELDEN RING\Game"
]

GAME_PROCESS = "eldenring.exe"

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return data.get("game_path")
    return None

def save_config(game_path):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"game_path": game_path}, f)

def find_game_path():
    game_path = load_config()
    if game_path and Path(game_path).exists():
        return game_path
    for path in COMMON_PATHS:
        exe_path = Path(path) / GAME_PROCESS
        if exe_path.exists():
            save_config(str(exe_path))
            return str(exe_path)
    while True:
        user_path = input("Enter the full path to Elden Ring's eldenring.exe: ").strip()
        if Path(user_path).exists():
            save_config(user_path)
            return user_path
        print("Invalid path. Try again.")

def start_game(game_path):
    try:
        subprocess.Popen(game_path, shell=True)
        print(f"Starting Elden Ring from: {game_path}")
        return True
    except Exception as e:
        print(f"Failed to start the game: {e}")
        return False

def set_affinity(process_name):
    for process in psutil.process_iter(attrs=['pid', 'name']):
        if process.info['name'].lower() == process_name.lower():
            try:
                p = psutil.Process(process.info['pid'])
                available_cpus = list(range(psutil.cpu_count()))
                if 0 in available_cpus:
                    available_cpus.remove(0)
                p.cpu_affinity(available_cpus)
                print(f"Affinity set for {process_name}: {available_cpus}")
                return True
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                print(f"Access denied or process not found: {process_name}")
                return False
    return False

if __name__ == "__main__":
    if not is_admin():
        print("Please run this script as Administrator.")
        time.sleep(3)
        exit()
    game_path = find_game_path()
    if game_path and start_game(game_path):
        print("Waiting for Elden Ring to start...")
        while True:
            if set_affinity(GAME_PROCESS):
                break
            time.sleep(5)
