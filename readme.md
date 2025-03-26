# EldenRingStutterFix

![Elden Ring Stutter Fix](assests/image.jpg)

## Overview
**EldenRingStutterFix** is a simple mod that improves **Elden Ring**'s performance by automatically adjusting CPU affinity settings. It prevents the game from overloading **CPU Core 0**, which is primarily responsible for handling system tasks, resulting in smoother gameplay and reduced stuttering.

## Why This Fix Works
### Understanding CPU Cores and Core 0
A **CPU (Central Processing Unit)** has multiple **cores**, which are like individual workers that handle different tasks. Modern computers have multiple cores (e.g., **4, 6, 8, or more**) to allow multitasking and improve performance. The **operating system (Windows)** and background applications primarily use **Core 0** for essential system processes, such as handling input, running services, and managing memory.

### How Games Use CPU Cores
Most modern games are designed to use multiple CPU cores, but sometimes they fail to **efficiently distribute their workload**. Instead of spreading their processing across **all available cores**, some games end up using **Core 0** more than others. This can cause performance issues because Core 0 is already busy with system tasks, leading to **CPU congestion** and **stuttering** in the game.

### The Fix: Disabling Core 0 for Elden Ring
By manually **disabling Core 0** for Elden Ring, we force the game to distribute its workload to the remaining CPU cores. This helps in two key ways:
1. **Reduces congestion:** Since Core 0 is no longer handling both system processes and game processes, the operating system can run more smoothly.
2. **Forces better multithreading:** The game engine is forced to reassign tasks to other cores, which improves overall performance and reduces stuttering.

This fix is especially useful for games that are not well-optimized for multi-core CPUs and tend to rely too much on the **first core**.

## Features
✅ Automatically detects and applies the fix when **Elden Ring** is running.
✅ Disables **CPU Core 0** for the game process to reduce stuttering.
✅ Runs in the background without user intervention.
✅ Lightweight and easy to use – no extra dependencies required.
✅ No modifications to game files.

## Installation
1. **Download the latest release** from [GitHub Releases](#).
2. **Run `eldenring_stutteringfix.exe` as Administrator** (required for changing CPU affinity).
3. **Start Elden Ring** – the fix will be applied automatically.
4. Enjoy smoother gameplay!

## Issue: Affinity Reset on Game Restart
### **Problem**
The CPU affinity setting does **not persist** after restarting Elden Ring. Once the game is closed and reopened, **CPU 0 is re-enabled**, and the fix must be applied again manually by restarting the script.

### **Technical Explanation**
By default, Windows assigns all CPU cores to a running application. Elden Ring should ideally optimize thread distribution on its own, but since it does not properly avoid **Core 0**, manual intervention is needed. However, because CPU affinity settings are reset when a process restarts, this fix only works while the script is running.

