# Thalix

A high-performance process management and memory editing toolkit for eliminating game stuttering.

## T DPC Latency

DPC (Deferred Procedure Call) latency occurs when kernel routines take too long to execute, causing visible micro-stutters in games. When a game's rendering thread runs on Core 0 alongside high-priority system processes, DPC spikes starve the thread of CPU time even brief pauses of microseconds cause noticeable frame-time spikes.

**Common causes:** (so far)
- Inefficient device drivers
- Excessive I/O activity  
- Conflicts with high-priority processes



Thalix isolates game processes to dedicated CPU cores, away from system interrupts and DPC activity. This technique, a staple of real-time computing, ensures consistent frame times by preventing thread starvation.

## Features 
   Can fight Radhan without getting frame nuked 

## Usage

ugh check releases ?


Requires Python 3.8+ with CustomTkinter, psutil, and Pillow.
