import psutil  # Library to manage system processes
import time  # Library for time-related functions (sleep, delays)
import ctypes  # Library to check for admin privileges
import subprocess  # Library to start external processes (like games)
import os  # Library for OS file handling
import json  # Library to save and load configuration files
from pathlib import Path  # Library for working with file paths

# Configuration file to store the game path
CONFIG_FILE = "eldenring_config.json"

# Common installation paths for Elden Ring
COMMON_PATHS = [
    r"C:\Program Files (x86)\Steam\steamapps\common\ELDEN RING\Game",
    r"C:\Program Files\Steam\steamapps\common\ELDEN RING\Game",
    r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game",
    r"D:\Games\ELDEN RING\Game" ,
    r"D:\Game\ELDEN RING \Games",
    r"D:\Games\ELDEN RING\Games",
    
]  

# Name of the game process
GAME_PROCESS = "eldenring.exe"

def is_admin():
    """Check if the script is running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()  # Returns True if admin, False otherwise
    except:
        return False  # If check fails, assume not admin

def load_config():
    """Load the saved game path from the config file."""
    if os.path.exists(CONFIG_FILE):  # Check if config file exists
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)  # Load JSON data from file
            return data.get("game_path")  # Return the saved game path
    return None  # Return None if no config file exists

def save_config(game_path):
    """Save the game path to a config file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump({"game_path": game_path}, f)  # Save the game path in JSON format

def find_game_path():
    """Search for the game in common installation locations or prompt the user to enter it manually."""
    game_path = load_config()  # Load previously saved game path
    if game_path and Path(game_path).exists():  # Check if path exists
        return game_path

    for path in COMMON_PATHS:  # Loop through common installation paths
        exe_path = Path(path) / GAME_PROCESS  # Create full path to game executable
        if exe_path.exists():  # Check if executable exists
            save_config(str(exe_path))  # Save detected path
            return str(exe_path)  # Return found path

    # If not found, ask the user to input the path manually
    while True:
        user_path = input("Enter the full path to Elden Ring's eldenring.exe: ").strip()
        if Path(user_path).exists():  # Validate entered path
            save_config(user_path)  # Save manually entered path
            return user_path  # Return user-provided path
        print("Invalid path. Try again.")  # Ask again if invalid

def start_game(game_path):
    """Start Elden Ring using the found or entered game path."""
    try:
        subprocess.Popen(game_path, shell=True)  # Start the game
        print(f"Starting Elden Ring from: {game_path}")
        return True  # Return success
    except Exception as e:
        print(f"Failed to start the game: {e}")  # Print error if failed
        return False  # Return failure

def set_affinity(process_name):
    """Set CPU affinity for the specified process."""
    for process in psutil.process_iter(attrs=['pid', 'name']):  # Iterate through running processes
        if process.info['name'].lower() == process_name.lower():  # Match process name
            try:
                p = psutil.Process(process.info['pid'])  # Get process handle
                available_cpus = list(range(psutil.cpu_count()))  # Get all CPU cores
                if 0 in available_cpus:
                    available_cpus.remove(0)  # Remove CPU 0 to improve performance
                p.cpu_affinity(available_cpus)  # Apply CPU affinity
                print(f"Affinity set for {process_name}: {available_cpus}")
                return True  # Success
            except (psutil.AccessDenied, psutil.NoSuchProcess):  # Handle errors
                print(f"Access denied or process not found: {process_name}")
                return False  # Failure
    return False  # Return False if process not found

if __name__ == "__main__":
    if not is_admin():  # Check if script is running as administrator
        print("Please run this script as Administrator.")
        time.sleep(3)
        exit()  # Exit if not admin

    game_path = find_game_path()  # Get the game path
    if game_path and start_game(game_path):  # Start the game if path is valid
        print("Waiting for Elden Ring to start...")
        while True:
            if set_affinity(GAME_PROCESS):  # Set CPU affinity once game is detected
                break  # Exit loop once done
            time.sleep(5)  # Wait 5 seconds before checking again
