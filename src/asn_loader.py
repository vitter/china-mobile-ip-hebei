from pathlib import Path
from typing import List

def load_asns_from_file(path: str = "../data/cmcc.txt") -> List[int]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"ASN file not found: {p.resolve()}")
    text = p.read_text(encoding="utf-8")
    
    # 过滤掉注释行（以 // 或 # 开头的行）
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith('//') and not line.startswith('#'):
            lines.append(line)
    
    # 合并所有非注释行，按逗号分割
    combined = ','.join(lines)
    parts = [x.strip() for x in combined.split(',') if x.strip()]
    
    asns = []
    for part in parts:
        try:
            asns.append(int(part))
        except ValueError:
            continue
    return asns

if __name__ == "__main__":
    print(load_asns_from_file())
