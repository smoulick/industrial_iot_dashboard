import requests
from pathlib import Path

def download_from_huggingface(file_path: Path, hf_url: str):
    if not file_path.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        response = requests.get(hf_url)
        if response.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(response.content)
        else:
            raise RuntimeError(f"Failed to download {hf_url} (Status code: {response.status_code})")
