"""Adapter for trusted local EIM executables. Does not use cloud credentials."""
import math
import subprocess


def adapt_output(result, config, width, height):
    kind, mapping = config["output_type"], config["label_map"]
    if kind not in result:
        raise ValueError("Saída do modelo incompatível")
    if kind == "classification":
        raw = [{"label": k, "value": v} for k, v in result[kind].items()]
    else:
        raw = result[kind]
    if len(raw) > 100:
        raise ValueError("Muitas detecções na captura")
    detections = []
    for item in raw:
        if item["label"] not in mapping:
            continue
        confidence = float(item["value"])
        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("Confiança inválida")
        bbox = None
        if kind == "bounding_boxes":
            bbox = [item["x"] / width, item["y"] / height,
                    item["width"] / width, item["height"] / height]
            if any(not math.isfinite(v) or not 0 <= v <= 1 for v in bbox) or bbox[0]+bbox[2] > 1.000001 or bbox[1]+bbox[3] > 1.000001:
                raise ValueError("Coordenadas inválidas")
        detections.append({"label": mapping[item["label"]], "confidence": confidence, "bbox": bbox})
    return detections


class Detector:
    def __init__(self, config):
        from edge_impulse_linux.image import ImageImpulseRunner

        class OwnedRunner(ImageImpulseRunner):
            # The upstream stop() recursively removes its temp directory and does not wait
            # for the process. On a borrowed device we only close our IPC/process resources.
            def stop(self):
                client = getattr(self, "_client", None)
                if client is not None:
                    client.close()
                    self._client = None
                process = getattr(self, "_runner", None)
                if process is not None:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=2)
                    self._runner = None
                # Preserve the SDK's own temporary socket directory; never remove files.
                self._tempdir = None

        self.config = config
        self.runner = OwnedRunner(config["model_path"])
        # Socket IPC avoids shared-memory cleanup outside our process ownership.
        self.runner._allow_shm = False
        self.runner._timeout = 10
        try:
            info = self.runner.init()
            params = info["model_parameters"]
            # Old exports silently use squash in the SDK; require explicit Studio settings.
            if params.get("image_resize_mode") not in ("squash", "fit-shortest", "fit-longest"):
                raise ValueError("Reexporte o modelo com image_resize_mode explícito")
            if set(config["label_map"]) - set(params["labels"]):
                raise ValueError("Mapeamento contém classes inexistentes no modelo")
            self.labels = sorted(set(config["label_map"].values()))
        except BaseException:
            self.close()
            raise

    def infer(self, frame):
        import cv2
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        features, cropped = self.runner.get_features_from_image_auto_studio_settings(rgb)
        try:
            raw = self.runner.classify(features)["result"]
        except TimeoutError:
            raise
        except Exception as exc:
            raise RuntimeError("Falha de inferência do modelo") from exc
        height, width = cropped.shape[:2]
        detections = adapt_output(raw, self.config, width, height)
        bgr = cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR) if cropped.ndim == 3 else cropped
        return detections, jpeg(bgr)

    def close(self):
        self.runner.stop()


def jpeg(frame):
    import cv2
    ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
    if not ok or encoded.nbytes > 1024 * 1024:
        raise ValueError("Falha ao codificar JPEG dentro do limite de 1 MB")
    return encoded.tobytes()
