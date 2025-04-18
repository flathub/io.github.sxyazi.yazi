"""
Copyright (c) 2024 - lihaohong6
License: MIT
"""
import re
import shutil
import subprocess
from pathlib import Path

import requests

flatpak_cargo_generator_path = Path("./flatpak-cargo-generator.py")

def ensure_flatpak_cargo_generator_exists():
    if flatpak_cargo_generator_path.exists():
        return
    url = "https://raw.githubusercontent.com/flatpak/flatpak-builder-tools/refs/heads/master/cargo/flatpak-cargo-generator.py"
    res = requests.get(url)
    with flatpak_cargo_generator_path.open("w") as f:
        f.write(res.text)


def cleanup_flatpak_cargo_generator():
    flatpak_cargo_generator_path.unlink()


def update_rust_library(library: str, tag: str, out_path: str) -> None:
    url = f"https://raw.githubusercontent.com/{library}/refs/tags/{tag}/Cargo.lock"
    res = requests.get(url)
    cargo_lock_path = Path("./cargo.lock")
    with cargo_lock_path.open("w") as f:
        f.write(res.text)
    subprocess.run(["python",
                    flatpak_cargo_generator_path,
                    cargo_lock_path,
                    "-o",
                    out_path])
    cargo_lock_path.unlink()


def get_tag(yaml_file: str, library: str) -> str:
    return re.search(rf"{library}.git.*\n.*tag: (.*)\n", yaml_file).group(1)


def get_yaml_file_as_text() -> str:
    yml_files = list(Path(".").rglob("*.yml"))
    result = []
    for yml_file in yml_files:
        if not yml_file.is_file():
            continue
        with yml_file.open("r") as f:
            result.append(f.read())
    return "\n".join(result)


def get_library_path(library_name: str) -> Path:
    p = Path(f"modules/{library_name}")
    p.mkdir(parents=True, exist_ok=True)
    return p


def cargo_main():
    ensure_flatpak_cargo_generator_exists()
    yaml_file = get_yaml_file_as_text()
    for library in ("sxyazi/yazi", "ajeetdsouza/zoxide", "BurntSushi/ripgrep", "sharkdp/fd", "linebender/resvg"):
        tag = get_tag(yaml_file, library)
        library_name = library.split('/')[-1]
        if library_name == "yazi":
            target = f"cargo-sources-{library_name}.json"
        else:
            library_path = get_library_path(library_name)
            target = library_path/ "cargo-sources.json"
        update_rust_library(library, tag, target)
    cleanup_flatpak_cargo_generator()


def golang_main():
    yaml_file = get_yaml_file_as_text()
    for library in ("junegunn/fzf", "1player/host-spawn"):
        library_name = library.split('/')[-1]
        library_path = get_library_path(library_name)
        tag = get_tag(yaml_file, library)

        clone_dir = Path(library_name)
        subprocess.run(["git",
                        "clone",
                        "--depth", "1",
                        "--branch", tag,
                        f"https://github.com/{library}"])
        subprocess.run(["flatpak-go-mod", clone_dir])
        shutil.rmtree(clone_dir)

        # flatpak-go-mod defaults to using modules.txt. Need to specify the subdirectory instead.
        yml_path = Path("go.mod.yml")
        with open(yml_path, "r+") as f:
            content = f.read().replace("path: modules.txt", f"path: modules/{library_name}/modules.txt")
            f.seek(0)
            f.write(content)
            f.truncate()

        # Move to subdirectories to avoid overcrowding the base directory
        yml_path.rename(library_path / "sources.yml")
        Path("modules.txt").rename(library_path / "modules.txt")


if __name__ == "__main__":
    cargo_main()
    golang_main()
