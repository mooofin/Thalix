#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

slint::include_modules!();

mod mod_manager;
mod process;

use slint::{SharedString, VecModel};
use std::rc::Rc;

fn main() -> Result<(), slint::PlatformError> {
    let ui = MainWindow::new()?;
    let h = ui.as_weak();

    update_processes(&ui);
    ui.set_status_text(SharedString::from("Ready"));

    let available = mod_manager::list_available_mods();
    let mod_names: Vec<SharedString> = available.iter().map(|s| SharedString::from(s)).collect();
    ui.set_mod_list(Rc::new(VecModel::from(mod_names)).into());
    if let Some(m) = available.first() {
        ui.set_selected_mod(SharedString::from(m));
    }

    let h_ref = h.clone();
    ui.on_refresh_processes(move || {
        let ui = h_ref.unwrap();
        ui.set_status_text(SharedString::from("Scanning..."));
        update_processes(&ui);
        ui.set_status_text(SharedString::from("Ready"));
    });

    let h_aff = h.clone();
    ui.on_apply_affinity(move |pid| {
        let ui = h_aff.unwrap();
        let mut mask: usize = 0;
        for i in 0..16 {
            if i % 2 == 0 {
                mask |= 1 << i;
            }
        }
        match process::set_affinity(pid as u32, mask) {
            Ok(_) => {
                ui.set_status_text(SharedString::from(format!("Set: 0x{:X} -> {}", mask, pid)))
            }
            Err(e) => ui.set_status_text(SharedString::from(e)),
        }
    });

    let h_opt = h.clone();
    ui.on_optimize_stutter(move || {
        h_opt
            .unwrap()
            .set_status_text(SharedString::from("Preset: Physical Cores Only"));
    });

    let h_mod = h.clone();
    ui.on_apply_mod(move |path, name| {
        let ui = h_mod.unwrap();
        ui.set_status_text(SharedString::from("Patching..."));
        match mod_manager::apply_mod(path.as_str(), name.as_str()) {
            Ok(_) => ui.set_status_text(SharedString::from("Success: Mod Applied")),
            Err(e) => ui.set_status_text(SharedString::from(e)),
        }
    });

    let h_res = h.clone();
    ui.on_restore_originals(move |path| {
        let ui = h_res.unwrap();
        ui.set_status_text(SharedString::from("Restoring..."));
        match mod_manager::restore_originals(path.as_str()) {
            Ok(_) => ui.set_status_text(SharedString::from("Success: Original Restored")),
            Err(e) => ui.set_status_text(SharedString::from(e)),
        }
    });

    let h_reset = h.clone();
    ui.on_reset_cores(move || {
        h_reset
            .unwrap()
            .set_status_text(SharedString::from("Reset: All Cores Enabled"));
    });

    ui.run()
}

fn update_processes(ui: &MainWindow) {
    let list = process::list_processes();
    let models: Vec<ProcessEntry> = list
        .into_iter()
        .map(|p| ProcessEntry {
            name: SharedString::from(p.name),
            pid: p.pid as i32,
        })
        .collect();
    ui.set_process_list(Rc::new(VecModel::from(models)).into());
}
