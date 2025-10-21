# Thalix

A high-performance process management and memory editing toolkit for eliminating game stuttering.

## The Problem: DPC Latency

DPC (Deferred Procedure Call) latency occurs when kernel routines take too long to execute, causing visible micro-stutters in games. When a game's rendering thread runs on Core 0 alongside high-priority system processes, DPC spikes starve the thread of CPU time even brief pauses of microseconds cause noticeable frame-time spikes.

**Common causes:**
- Inefficient device drivers
- Excessive I/O activity  
- Conflicts with high-priority processes

## The Solution

Thalix isolates game processes to dedicated CPU cores, away from system interrupts and DPC activity. This technique, a staple of real-time computing, ensures consistent frame times by preventing thread starvation.

**Features:**
- CPU affinity management with per-core monitoring
- Process priority control
- Built-in memory editor with cheat table support
- Real-time performance statistics
- Configuration presets

## Usage

```bash
python run_gui.py
```

Requires Python 3.8+ with CustomTkinter, psutil, and Pillow.
