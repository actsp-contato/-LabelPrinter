import base64
import json
import os
import time
import urllib.error
import urllib.request

from printer import print_raw


APP_URL = os.getenv("LABELPRINTER_URL", "http://127.0.0.1:5000").rstrip("/")
TOKEN = os.getenv("PRINT_AGENT_TOKEN", "")
PRINTER_NAME = os.getenv("PRINTER_NAME") or None
POLL_SECONDS = max(2, int(os.getenv("POLL_SECONDS", "5")))


def _request(path, method="GET", payload=None):
    data = None
    headers = {"X-Print-Agent-Token": TOKEN}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{APP_URL}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _complete(job_id, status, printer_name="", error_message=""):
    return _request(
        f"/api/print-jobs/{job_id}/complete",
        method="POST",
        payload={"status": status, "printer_name": printer_name, "error_message": error_message},
    )


def main():
    if not TOKEN:
        raise SystemExit("Defina a variável PRINT_AGENT_TOKEN antes de iniciar o agente.")

    print(f"Agente conectado em {APP_URL}. Pressione Ctrl+C para encerrar.")
    while True:
        try:
            payload = _request("/api/print-jobs/next")
            job = payload.get("job")
            if not job:
                time.sleep(POLL_SECONDS)
                continue

            data = base64.b64decode(job["data_base64"])
            used_printer = ""
            for _ in range(max(1, int(job.get("copies", 1)))):
                used_printer = print_raw(data, PRINTER_NAME)
            _complete(job["id"], "printed", printer_name=used_printer)
            print(f"Job {job['id']} impresso em {used_printer}: {job['label_name']}")
        except KeyboardInterrupt:
            print("Agente encerrado.")
            break
        except urllib.error.HTTPError as error:
            print(f"Erro HTTP {error.code}: confira URL e PRINT_AGENT_TOKEN.")
            time.sleep(POLL_SECONDS)
        except Exception as error:
            job_id = locals().get("job", {}).get("id") if isinstance(locals().get("job"), dict) else None
            if job_id:
                try:
                    _complete(job_id, "error", printer_name=PRINTER_NAME or "", error_message=str(error))
                except Exception:
                    pass
            print(f"Erro no agente: {error}")
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
