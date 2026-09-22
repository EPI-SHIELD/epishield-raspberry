import argparse
from datetime import datetime, timezone, timedelta
import json
import logging
import os
import sys
import signal
import threading
import time

import requests

from .config import load
from .camera import Camera
from .detector import Detector, jpeg

log = logging.getLogger("epishield")


def inference_timeout(*_):
    raise TimeoutError("Inferência excedeu o prazo")


class Client:
    def __init__(self, config):
        self.base = config["api_url"]
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers["Authorization"] = f"Bearer {config['token']}"
        self.session.verify = config.get("ca_bundle") or True

    def call(self, method, path, **kwargs):
        response = self.session.request(method, self.base + path, timeout=(3, 5), allow_redirects=False, **kwargs)
        if 300 <= response.status_code < 400:
            raise RuntimeError("Redirecionamento da API recusado")
        response.raise_for_status()
        return None if response.status_code == 204 else response.json()

    def close(self):
        self.session.close()


def collect(job, camera, detector, client, offset):
    """Fresh captures only; retain ten small detection lists and one representative JPEG."""
    rule = job["rule"]
    if rule != {"version": "temporal-v1", "samples": 10, "min_hits": 8, "confidence": 0.8,
                "min_span_seconds": 3, "timeout_seconds": 60}:
        raise ValueError("Versão de regra não suportada pelo agente")
    if set(job["required_epis"]) - set(detector.labels):
        raise ValueError("Modelo incompatível com os EPIs obrigatórios")
    if job["model"] != {"version": detector.config["model_version"], "sha256": detector.config["model_sha256"]}:
        raise ValueError("Modelo difere da solicitação")
    samples, best_photo, best_count, photo_sequence = [], None, 101, None
    start = time.monotonic()
    expires = datetime.fromisoformat(job["expires_at"])
    created = datetime.fromisoformat(job["created_at"])
    first_capture = None
    for index in range(10):
        # Wait on monotonic time; inference duration is allowed to exceed the spacing.
        spacing = max(3.05 / 9, detector.config.get("sample_interval_seconds", .34))
        due = start if first_capture is None else first_capture + index * spacing
        time.sleep(max(0, due-time.monotonic()))
        _, captured, mono, frame = camera.fresh(max(start, time.monotonic() - 0.001))
        first_capture = mono if first_capture is None else first_capture
        captured += timedelta(seconds=offset)
        if captured < created or captured >= expires:
            raise RuntimeError("Captura fora da janela da inspeção")
        detections, photo = detector.infer(frame)
        if datetime.now(timezone.utc) + timedelta(seconds=offset) >= expires:
            raise RuntimeError("Tempo de inspeção esgotado")
        samples.append({"sequence": index+1, "captured_at": captured.isoformat(), "detections": detections})
        hits = {d["label"] for d in detections if d["confidence"] >= rule["confidence"]}
        count = len(hits.intersection(job["required_epis"]))
        if count < best_count:
            best_count, best_photo, photo_sequence = count, photo, index+1
        try:
            client.call("POST", f"/edge/inspections/{job['id']}/progress", json={"completed": index+1})
        except requests.RequestException:
            pass  # progress is best effort; evidence is sent atomically below
    return {"samples": samples, "photo_sequence": photo_sequence,
            "model_version": detector.config["model_version"],
            "model_sha256": detector.config["model_sha256"]}, best_photo


def send_result(client, job, payload, photo, stop):
    # Same serialized evidence/photo across retries; never re-capture after uncertain delivery.
    for delay in (0, 1, 2, 4, 8):
        if stop.wait(delay):
            return False
        try:
            client.call("POST", f"/edge/inspections/{job['id']}/result",
                        data={"evidence": json.dumps(payload)}, files={"photo": ("capture.jpg", photo, "image/jpeg")})
            return True
        except requests.HTTPError as exc:
            status = exc.response.status_code
            if status < 500 and status not in (408, 429):
                log.warning("Resultado rejeitado pela API (HTTP %s)", status)
                return False
        except requests.RequestException:
            pass
    log.warning("Resultado não confirmado; inspeção poderá expirar")
    return False


def run(config):
    stop, busy = threading.Event(), threading.Event()
    client, camera, detector = Client(config), None, None
    telemetry = {"offset": 0.0, "ready": False, "error": None}
    synchronized = threading.Event()
    handled = None
    health_thread = None
    old_handler = None
    try:
        # Linux-only alarm bounds a stuck native inference/IPC call; shutdown stops our runner.
        old_handler = signal.signal(signal.SIGALRM, inference_timeout)
        signal.alarm(20)
        detector = Detector(config)
        signal.alarm(0)
        camera = Camera(config.get("camera", 0))
        _, _, _, frame = camera.fresh(time.monotonic())
        signal.alarm(15)
        detector.infer(frame)  # verify output/preprocessing before advertising ready
        signal.alarm(0)
        telemetry["ready"] = True

        def heartbeat_loop():
            health_client = Client(config)
            due, preview_until = 0, 0
            try:
                while not stop.is_set():
                    now = time.monotonic()
                    try:
                        if now >= due:
                            before = datetime.now(timezone.utc)
                            result = health_client.call("POST", "/edge/heartbeat", json={
                                "model_version": config["model_version"], "model_sha256": config["model_sha256"],
                                "labels": detector.labels, "ready": telemetry["ready"] and not camera.error,
                                "error": camera.error or telemetry["error"]})
                            midpoint = before + (datetime.now(timezone.utc)-before)/2
                            telemetry["offset"] = (datetime.fromisoformat(result["server_time"]) - midpoint).total_seconds()
                            synchronized.set()
                            preview_until = time.monotonic() + 10 if result["preview_requested"] else 0
                            due = time.monotonic() + 10
                        if config.get("preview_enabled", True) and time.monotonic() < preview_until and not busy.is_set() and not camera.error:
                            import cv2
                            _, _, _, current = camera.fresh(time.monotonic()-0.5)
                            small = cv2.resize(current, (config.get("preview_width", 640), config.get("preview_height", 480)))
                            health_client.call("PUT", "/edge/preview", data=jpeg(small), headers={"Content-Type": "image/jpeg"})
                    except requests.HTTPError as exc:
                        if exc.response.status_code in (401, 403):
                            stop.set()
                        due = time.monotonic() + 10
                    except (requests.RequestException, RuntimeError, ValueError):
                        due = time.monotonic() + 10
                    stop.wait(max(.52, 1 / config.get("preview_fps", 2)))
            finally:
                health_client.close()

        health_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        health_thread.start()
        log.info("Agente iniciado; mantenha uma pessoa enquadrada. Ctrl+C encerra.")
        while not stop.wait(0.5):
            if not synchronized.is_set():
                continue
            try:
                job = client.call("GET", "/edge/inspections/next")
                if not job or job["id"] == handled:
                    continue
                handled = job["id"]
                busy.set()
                try:
                    # Reserve time for submission; server remains authoritative on expiry.
                    signal.alarm(45)
                    payload, photo = collect(job, camera, detector, client, telemetry["offset"])
                    signal.alarm(0)
                    send_result(client, job, payload, photo, stop)
                except (RuntimeError, ValueError, TimeoutError) as exc:
                    signal.alarm(0)
                    try:
                        client.call("POST", f"/edge/inspections/{job['id']}/progress",
                                    json={"completed": 0, "error": str(exc)[:300]})
                    except requests.RequestException:
                        pass
                    if isinstance(exc, TimeoutError):
                        telemetry.update(ready=False, error="Inferência excedeu o prazo; reinicie o agente")
                        break
                finally:
                    signal.alarm(0)
                    busy.clear()
            except requests.HTTPError as exc:
                if exc.response.status_code in (401, 403):
                    break
                stop.wait(2)
            except requests.RequestException:
                stop.wait(2)
    except KeyboardInterrupt:
        log.info("Encerrando")
    finally:
        stop.set()
        signal.alarm(0)
        if camera:
            camera.close()
        if health_thread:
            health_thread.join(timeout=9)
        if detector:
            detector.close()
        client.close()
        if old_handler is not None:
            signal.signal(signal.SIGALRM, old_handler)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("O agente de câmera deve rodar em Linux; testes sem hardware também funcionam em outros sistemas")
    if os.geteuid() == 0:
        parser.error("Execute como usuário comum, sem root/sudo")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run(load(args.config))


if __name__ == "__main__":
    main()
