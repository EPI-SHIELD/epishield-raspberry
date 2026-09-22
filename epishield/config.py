import hashlib
import json
import os
from pathlib import Path
import re
import stat
import math
from urllib.parse import urlparse


def load(path):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    url = urlparse(config["api_url"])
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError("API deve usar HTTPS sem credenciais ou parâmetros na URL")
    config["api_url"] = config["api_url"].rstrip("/")
    token_path = Path(config["token_file"])
    if os.name == "posix" and stat.S_IMODE(token_path.stat().st_mode) & 0o077:
        raise ValueError("Credencial deve ter permissão 0600")
    config["token"] = token_path.read_text().strip()
    if not 32 <= len(config["token"]) <= 256:
        raise ValueError("Credencial inválida")
    model_path = Path(config["model_path"]).resolve(strict=True)
    with model_path.open("rb") as file:
        hasher = hashlib.sha256()
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
        actual = hasher.hexdigest()
    if actual != config["model_sha256"]:
        raise ValueError("Hash do modelo não confere")
    config["model_path"] = str(model_path)
    if not config.get("model_version") or len(config["model_version"]) > 100:
        raise ValueError("Informe versão do modelo")
    mapping = config["label_map"]
    if not mapping or not all(re.fullmatch(r"[a-z0-9_]{1,60}", v) for v in mapping.values()):
        raise ValueError("Mapeamento de classes inválido")
    if config["output_type"] not in ("bounding_boxes", "classification"):
        raise ValueError("Formato do modelo não suportado")
    if config["output_type"] == "classification" and not config.get("classification_is_multilabel"):
        raise ValueError("Classificador exclusivo não permite confirmar múltiplos EPIs; valide modelo multilabel")
    for field, default, low, high in (("preview_fps", 2, 0.1, 2), ("sample_interval_seconds", .34, .34, 4),
                                     ("preview_width", 640, 64, 640), ("preview_height", 480, 64, 480)):
        value = config.setdefault(field, default)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"Configuração inválida: {field}")
        if field in ("preview_width", "preview_height") and not isinstance(value, int):
            raise ValueError(f"Dimensão deve ser inteira: {field}")
    return config
