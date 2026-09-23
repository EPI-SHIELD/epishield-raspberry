from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

import requests

from epishield.config import load
from epishield.detector import adapt_output
from epishield.agent import Client, collect, send_result

RULE = {"version": "temporal-v1", "samples": 10, "min_hits": 8, "confidence": .8,
        "min_span_seconds": 3, "timeout_seconds": 60}


class AgentTests(unittest.TestCase):
    def test_mapping_and_normalized_boxes(self):
        config = {"output_type": "bounding_boxes", "label_map": {"helmet": "capacete"}}
        result = adapt_output({"bounding_boxes": [{"label": "helmet", "value": .8,
                             "x": 10, "y": 20, "width": 30, "height": 40}]}, config, 100, 100)
        self.assertEqual(result[0], {"label": "capacete", "confidence": .8, "bbox": [.1, .2, .3, .4]})
        with self.assertRaises(ValueError): adapt_output({"classification": {}}, config, 100, 100)

    def test_invalid_confidence(self):
        config = {"output_type": "classification", "label_map": {"helmet": "capacete"}}
        for confidence in (float("nan"), 1.1, -1):
            with self.assertRaises(ValueError):
                adapt_output({"classification": {"helmet": confidence}}, config, 100, 100)

    def test_fresh_capture_consensus_and_representative_photo(self):
        start = datetime.now(timezone.utc)
        job = {"id": "inspection", "created_at": start.isoformat(),
               "expires_at": (start+timedelta(seconds=60)).isoformat(), "required_epis": ["capacete"],
               "rule": RULE, "model": {"version": "v1", "sha256": "a"*64}}
        detector = Mock(labels=["capacete"], config={"model_version": "v1", "model_sha256": "a"*64})
        detector.infer.side_effect = [([{"label": "capacete", "confidence": .8}], b"photo") for _ in range(8)] + [([], b"worst"), ([], b"last")]
        camera = Mock()
        camera.fresh.side_effect = [(i+1, start+timedelta(seconds=1+i*.4), 101+i*.4, object()) for i in range(10)]
        with patch("epishield.agent.time.monotonic", return_value=100), patch("epishield.agent.time.sleep"):
            result, photo = collect(job, camera, detector, Mock(), 0)
        self.assertEqual(len(result["samples"]), 10)
        self.assertEqual(camera.fresh.call_count, 10)
        self.assertEqual(result["photo_sequence"], 9)
        self.assertEqual(photo, b"worst")
        self.assertGreaterEqual((datetime.fromisoformat(result["samples"][-1]["captured_at"])-datetime.fromisoformat(result["samples"][0]["captured_at"])).total_seconds(), 3)

    def test_retry_preserves_evidence(self):
        client = Mock()
        client.call.side_effect = [requests.ConnectionError(), {"state": "completed"}]
        stop = Mock()
        stop.wait.return_value = False
        self.assertTrue(send_result(client, {"id": "id"}, {"samples": [1]}, b"photo", stop))
        self.assertEqual(client.call.call_args_list[0], client.call.call_args_list[1])

    def test_permanent_error_does_not_retry(self):
        client = Mock()
        response = requests.Response(); response.status_code = 409
        client.call.side_effect = requests.HTTPError(response=response)
        stop = Mock(); stop.wait.return_value = False
        self.assertFalse(send_result(client, {"id": "id"}, {}, b"photo", stop))
        self.assertEqual(client.call.call_count, 1)

    def test_tls_and_no_redirects(self):
        client = Client({"api_url": "https://test", "token": "x"*32})
        client.session.request = Mock()
        client.session.request.return_value.status_code = 302
        with self.assertRaises(RuntimeError): client.call("GET", "/edge/inspections/next")
        self.assertTrue(client.session.verify)
        self.assertFalse(client.session.trust_env)
        self.assertFalse(client.session.request.call_args.kwargs["allow_redirects"])
        client.close()

    def test_install_refuses_existing_directory(self):
        spec = importlib.util.spec_from_file_location("installer", Path(__file__).resolve().parents[1]/"scripts/install.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        # No cleanup operations in the application: this fixture owns its test directory.
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/"owner.txt"; path.write_text("preserve")
            with self.assertRaises(ValueError): module.install(root, dependencies=False)
            self.assertEqual(path.read_text(), "preserve")

    def test_config_rejects_http_and_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            token = directory/"agent.token"; token.write_text("x"*32); token.chmod(0o600)
            model = directory/"model.eim"; model.write_bytes(b"model")
            config = {"api_url": "http://192.168.1.2", "token_file": str(token), "model_path": str(model),
                      "model_sha256": hashlib.sha256(b"model").hexdigest(), "model_version": "v1",
                      "label_map": {"helmet": "capacete"}, "output_type": "bounding_boxes"}
            path = directory/"config.json"
            path.write_text(json.dumps(config))
            with self.assertRaises(ValueError): load(path)
            config["api_url"] = "https://test"; config["model_sha256"] = "a"*64
            path.write_text(json.dumps(config))
            with self.assertRaises(ValueError): load(path)
            config["model_sha256"] = hashlib.sha256(b"model").hexdigest()
            path.write_text(json.dumps(config))
            self.assertEqual(load(path)["model_version"], "v1")


if __name__ == "__main__": unittest.main()
