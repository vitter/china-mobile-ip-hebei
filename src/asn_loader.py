from pathlib import Path
from typing import List

def load_asns_from_file(path: str = "../data/cmcc.txt") -> List[int]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"ASN file not found: {p.resolve()}")
    text = p.read_text(encoding="utf-8")
    parts = [x.strip() for x in text.replace("\n", "").split(",") if x.strip()]
    asns = []
    for part in parts:
        try:
            asns.append(int(part))
        except ValueError:
            continue
    return asns

if __name__ == "__main__":
    print(load_asns_from_file())
