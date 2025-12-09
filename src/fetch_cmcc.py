import requests
from pathlib import Path

RAW_URL = "https://raw.githubusercontent.com/vitter/china-mainland-asn/refs/heads/main/asn_txt/cmcc.txt"
OUT_PATH = Path("../data/cmcc.txt")

def download_cmcc(url=RAW_URL, out_path=OUT_PATH):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    out_path.write_text(r.text, encoding="utf-8")
    print(f"Saved cmcc.txt -> {out_path.resolve()}")

if __name__ == "__main__":
    download_cmcc()
