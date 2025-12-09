# 河北省中国移动 IP 段扫描器（ip2region + bgp.tools）

本仓库自动获取中国移动 ASN 列表（来自 data/cmcc.txt），并通过 bgp.tools 并发拉取 ASN 对应前缀（CIDR），
使用本地 ip2region xdb 做离线高速 IP->省/运营商 判断，按采样结果将前缀分层（high/medium/none），
最终输出去重的河北省中国移动 CIDR 列表，并在 README 中生成按省份统计表。

## 特性（A2 完整自动化版）
- 并发从 bgp.tools 获取 prefixes（asyncio + aiohttp）
- CIDR 多点随机采样，提升大网段准确率（可配置 sample 数量）
- 结果按置信度分层：`high`（所有样本命中） / `medium`（部分命中） / `none`
- 自动下载 ip2region_v4.xdb（若 data/ip2region.xdb 不存在）
- GitHub Actions: 定时运行并提交 output/ 和 README.md 更新

## 快速开始（本地）
1. 克隆仓库并进入目录（或解压 ZIP）
2. 准备 Python 虚拟环境并安装依赖：
   ```bash
   python -m venv .venv
   source .venv/bin/activate    # Windows 用户请用 .venv\\Scripts\\activate
   pip install -r requirements.txt
   ```
3. （可选）将 data/cmcc.txt 替换为你自己的 ASN 列表（逗号分隔）
4. 运行（自动下载 ip2region 数据库并执行扫描）：
   ```bash
   python src/main.py --cmcc data/cmcc.txt --sample 3 --use-cache
   ```
5. 查看输出：`output/hebei_cmcc_cidr.txt`, `output/hebei_cmcc_cidr.csv`, `output/hebei_cmcc_cidr.json`，以及自动生成的 README 中统计表。

## GitHub Actions
工作流位于 `.github/workflows/update.yml`，会定时（每日）运行，自动更新结果并提交到仓库。
注意：Actions 需要 `data/ip2region.xdb` 可用。脚本会尝试自动下载官方 `ip2region_v4.xdb` 到 `data/ip2region.xdb`（如有网络访问权限）。

---
