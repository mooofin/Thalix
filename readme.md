# Thalix
![Thalix Banner](./ui/assets/readme-banner.jpg)

### Before Thalix
![Before Thalix](./ui/assets/before-thalix.jpg)

### After Thalix
![After Thalix](./ui/assets/after-thalix.jpg)

Thalix is a high-performance process isolation and mod management engine designed to eliminate micro-stuttering in latency-sensitive applications. It provides a toolkit for hard-locking execution threads to physical cores and managing non-destructive folder-level game modifications through an atomic, safety-first deployment framework.

DPC (Deferred Procedure Call) latency is the primary bottleneck where kernel-mode routines (like I/O or driver interrupts) defer execution and inadvertently starve application threads of CPU cycles. Thalix mitigates this by isolating processes away from Core 0 and mapping them onto physical core masks, utilizing direct system calls to ensure execution priority and consistent frame pacing.

The mod management system employs a non-destructive state swapping mechanism to facilitate Quality of Life enhancements like the Better Bonfire Menu and DSR Easy Mode. Before any payload is applied, the engine renames original folders to `.original` backups, ensuring the vanilla state is preserved and allowing for one-click restoration.

## Further Reading
- [LatencyMon: Real-time latency checker](https://www.resplendence.com/latencymon)
- [Solving DPC Latency Issues](https://www.sweetwater.com/sweetcare/articles/solving-dpc-latency-issues/)
- [Driver 516.94 Audio/DPC Issues](https://forums.developer.nvidia.com/t/driver-version-516-94-introduces-high-dpc-latency-and-serious-audio-problems/238290)
- [Understanding DPCs in Windows](https://medium.com/@WaterBucket/understanding-deferred-procedure-calls-dpcs-in-windows-ecd138292883)
- [DPC Prioritization Theory](https://flylib.com/books/en/2.14.1.26/1/?)
- [Microsoft: Introduction to DPC Objects](https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/introduction-to-dpc-objects)
- [Wikipedia: Deferred Procedure Call](https://en.wikipedia.org/wiki/Deferred_Procedure_Call)

## Build
```bash
cargo build --release
./target/release/thalix-rust.exe
```
