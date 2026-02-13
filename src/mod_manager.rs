use std::fs;
use std::path::Path;

pub fn list_available_mods() -> Vec<String> {
    let mut mods = Vec::new();
    let extracted_path = Path::new("mods/extracted");
    if let Ok(entries) = fs::read_dir(extracted_path) {
        for entry in entries.flatten() {
            if let Ok(file_type) = entry.file_type() {
                if file_type.is_dir() {
                    mods.push(entry.file_name().to_string_lossy().to_string());
                }
            }
        }
    }
    mods
}

pub fn apply_mod(game_path: &str, mod_name: &str) -> Result<(), String> {
    let game_root = Path::new(game_path);
    if !game_root.exists() {
        return Err("Path invalid".into());
    }

    let mod_source = Path::new("mods/extracted").join(mod_name);
    if !mod_source.exists() {
        return Err("Source missing".into());
    }

    let entries = fs::read_dir(&mod_source).map_err(|e| e.to_string())?;
    for entry in entries.flatten() {
        if let Ok(file_type) = entry.file_type() {
            if file_type.is_dir() {
                let name = entry.file_name();
                let dst = game_root.join(&name);
                let bak = game_root.join(format!("{}.original", name.to_string_lossy()));

                if dst.exists() && !bak.exists() {
                    fs::rename(&dst, &bak).map_err(|e| e.to_string())?;
                }

                copy_dir_recursive(&mod_source.join(&name), &dst).map_err(|e| e.to_string())?;
            }
        }
    }
    Ok(())
}

pub fn restore_originals(game_path: &str) -> Result<(), String> {
    let root = Path::new(game_path);
    let entries = fs::read_dir(root).map_err(|e| e.to_string())?;

    for entry in entries.flatten() {
        let path = entry.path();
        let name = path.file_name().unwrap_or_default().to_string_lossy();

        if name.ends_with(".original") {
            let target = root.join(&name[..name.len() - 9]);
            if target.exists() {
                fs::remove_dir_all(&target).map_err(|e| e.to_string())?;
            }
            fs::rename(&path, &target).map_err(|e| e.to_string())?;
        }
    }
    Ok(())
}

fn copy_dir_recursive(src: &Path, dst: &Path) -> std::io::Result<()> {
    fs::create_dir_all(dst)?;
    for entry in fs::read_dir(src)? {
        let entry = entry?;
        let ty = entry.file_type()?;
        if ty.is_dir() {
            copy_dir_recursive(&entry.path(), &dst.join(entry.file_name()))?;
        } else {
            fs::copy(entry.path(), &dst.join(entry.file_name()))?;
        }
    }
    Ok(())
}
