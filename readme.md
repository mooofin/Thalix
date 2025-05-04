# EldenRingStutterFix

![image](https://github.com/user-attachments/assets/844ab760-4925-4e0c-a881-a503b6506393)




# Elden Ring Stutter Fix: CPU Affinity Optimization Mod  

## Overview  
**EldenRingStutterFix** is a performance optimization utility designed to mitigate stuttering and frame pacing issues in *Elden Ring* by dynamically adjusting CPU core allocation. This mod prevents the game from overloading **CPU Core 0**, which is primarily responsible for system-level operations, thereby improving overall gameplay smoothness and reducing micro-stutters.  

## Technical Background: Why This Fix Works  

### **1. CPU Core Utilization in Modern Systems**  
Modern CPUs consist of multiple cores (logical and physical) that handle concurrent processing tasks. The **operating system (Windows)** typically assigns critical system processes—such as input handling, driver operations, and background services—to **Core 0**. This core acts as the default scheduler hub, making it more susceptible to congestion when additional workloads are imposed.  

### **2. Game Engine Thread Scheduling & Havok Physics**  
*Elden Ring* utilizes **FromSoftware’s proprietary engine** alongside **Havok Physics** for collision detection, environmental interactions, and dynamic object simulations. The Havok engine, while efficient, has known threading limitations:  

- **Single-Threaded Physics Calculations**: Many legacy Havok implementations rely heavily on a single primary thread for physics computations.  
- **Poor Core Distribution**: Despite multi-core optimizations in modern Havok versions, some engine subsystems (e.g., particle effects, cloth simulation) may still default to **Core 0** due to legacy code dependencies.  
- **CPU Contention**: When both game logic and physics simulations compete for **Core 0**, latency spikes occur, manifesting as stutters during gameplay.  

### **3. Elden Ring’s Core Scheduling Issue**  
While *Elden Ring* is designed to leverage multiple CPU cores, empirical testing reveals:  
- **Uneven Workload Distribution**: The game frequently assigns an excessive number of high-priority threads to **Core 0**, neglecting underutilized cores.  
- **Background Process Interference**: Anticheat (Easy Anti-Cheat), DRM checks, and asset streaming further strain **Core 0**, exacerbating frame-time inconsistencies.  

### **4. The Solution: Forcing Optimal Core Allocation**  
By **excluding Core 0** from *Elden Ring’s* allowed CPU affinity mask, this mod:  
- **Reduces Core 0 Contention**: System tasks and game threads no longer compete for the same core.  
- **Encourages Better Thread Distribution**: The game engine is forced to utilize secondary cores (1, 2, 3, etc.) more effectively.  
- **Minimizes Stuttering**: Smoother frame delivery by preventing physics and rendering bottlenecks on Core 0.  

## Key Features  
 **Automatic CPU Affinity Adjustment** – Dynamically restricts *Elden Ring* from using Core 0.  
 **Background Operation** – No in-game overlay or manual configuration required.  
 **Non-Intrusive** – No game file modifications or DLL injections.  
 **Lightweight** – Minimal system resource usage (~1MB RAM).  

## Installation & Usage  
1. **Download** the latest release from the [GitHub repository](#).  
2. **Run `EldenRingStutterFix.exe` as Administrator** (required for CPU affinity adjustments).  
3. **Launch *Elden Ring*** – The fix applies automatically.  
4. **Verify Improved Performance** – Observe reduced stuttering and smoother frame pacing.  

