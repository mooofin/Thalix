# Thalix A high-performance process management and memory editing toolkit for eliminating game stuttering.
<img width="1886" height="1009" alt="image" src="https://github.com/user-attachments/assets/56013854-56c8-4c98-ba0b-26fa077641c3" />
<img width="1884" height="1004" alt="image" src="https://github.com/user-attachments/assets/e948a7ab-5466-4127-80a4-f89e9d3a8b18" />

## what the fuck  is DPC Latency ??
DPC (Deferred Procedure Call) latency occurs when kernel routines take too long to execute, causing visible micro-stutters in games. When a game's rendering thread runs on Core 0 alongside high-priority system processes, DPC spikes starve the thread of CPU time even brief pauses of microseconds cause noticeable frame-time spikes.

**Common causes:** (so far)

- Inefficient device drivers
- Excessive I/O activity
- Conflicts with high-priority processes

Thalix isolates game processes to dedicated CPU cores, away from system interrupts and DPC activity. This technique, a staple of real-time computing, ensures consistent frame times by preventing thread starvation.

## Features
Can fight Radhan without getting frame nuked
- Supports 2 mods now

## Usage
ugh check releases ?

