"""Install only inside a NEW directory, without sudo or system configuration changes."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv


def install(target, dependencies=True):
    source = Path(__file__).resolve().parents[1]
    target = Path(target).expanduser().absolute()
    if target.exists() or target.is_symlink():
        raise ValueError("Destino já existe; nada foi sobrescrito")
    parent = target.parent.resolve(strict=True)
    target = parent / target.name
    if target == source or source in target.parents:
        raise ValueError("Escolha pasta nova fora do checkout")
    target.mkdir(mode=0o700, exist_ok=False)
    # Explicit allowlist; never copies .git, credentials, models or unrelated files.
    for name in ("epishield", "scripts", "docs"):
        shutil.copytree(source / name, target / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("requirements.txt", "config.example.json", "README.md"):
        shutil.copyfile(source / name, target / name)
    venv.EnvBuilder(with_pip=True).create(target / ".venv")
    if dependencies:
        executable = target / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run([str(executable), "-m", "pip", "install", "--no-cache-dir", "--only-binary=:all:",
                        "--no-binary=edge-impulse-linux",
                        "-r", str(target / "requirements.txt")], check=True, cwd=target)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    args = parser.parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        sys.exit("Não execute como root/sudo")
    try:
        print("Instalado em", install(args.directory))
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        sys.exit(f"Instalação interrompida: {exc}. Nenhum arquivo foi removido; não reutilize destino parcial.")
