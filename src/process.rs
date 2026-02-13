use sysinfo::System;

pub struct ProcessInfo {
    pub pid: u32,
    pub name: String,
}

pub fn list_processes() -> Vec<ProcessInfo> {
    let mut sys = System::new_all();
    sys.refresh_all();
    sys.processes()
        .iter()
        .map(|(pid, p)| ProcessInfo {
            pid: pid.as_u32(),
            name: p.name().to_string(),
        })
        .collect()
}

#[cfg(target_os = "windows")]
pub fn set_affinity(pid: u32, mask: usize) -> Result<(), String> {
    use windows_sys::Win32::Foundation::{CloseHandle, FALSE, HANDLE};
    use windows_sys::Win32::System::Threading::{
        OpenProcess, PROCESS_QUERY_INFORMATION, PROCESS_SET_INFORMATION, SetProcessAffinityMask,
    };

    unsafe {
        let h: HANDLE = OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_SET_INFORMATION,
            FALSE,
            pid,
        );
        if h == 0 {
            return Err(format!("Open failed: {}", pid));
        }
        let res = SetProcessAffinityMask(h, mask);
        CloseHandle(h);
        if res != 0 {
            Ok(())
        } else {
            Err(format!("Affinity failed: {}", pid))
        }
    }
}

pub fn reset_all_affinity() {
    // Implement if needed, current sysinfo handles process refresh
}

#[cfg(target_os = "linux")]
pub fn set_affinity(pid: u32, mask: usize) -> Result<(), String> {
    use libc::{CPU_SET, CPU_ZERO, cpu_set_t, sched_setaffinity};
    use std::mem;

    unsafe {
        let mut set: cpu_set_t = mem::zeroed();
        CPU_ZERO(&mut set);
        for i in 0..(mem::size_of::<usize>() * 8) {
            if (mask & (1 << i)) != 0 {
                CPU_SET(i, &mut set);
            }
        }
        if sched_setaffinity(pid as i32, mem::size_of::<cpu_set_t>(), &set) == 0 {
            Ok(())
        } else {
            Err(format!("Sched failed: {}", pid))
        }
    }
}
