import psutil
import time
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
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
                return
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                print(f"Access denied or process not found: {process_name}")
                return
    print(f"{process_name} not found. Make sure the game is running.")

if __name__ == "__main__":
    if not is_admin():
        print("Please run this script as Administrator.")
        time.sleep(3)
        exit()
    
    game_process = "eldenring.exe"
    print("Waiting for Elden Ring to start...")
    while True:
        set_affinity(game_process)
        time.sleep(5)
