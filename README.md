# 河北省中国移动 IP 段扫描器

基于 ip2region v3.x 和 RIPEstat API 的自动化 IP 段识别工具，用于提取特定省份运营商的 CIDR 列表。

## 项目简介

本项目通过以下流程自动识别河北省中国移动的 IP 段：

1. **获取 ASN 列表**：从 `data/cmcc.txt` 读取中国移动的 ASN（自治系统号）
2. **获取 IP 前缀**：通过 RIPEstat API 并发查询每个 ASN 对应的 IPv4 CIDR 前缀
3. **智能采样分析**：对每个 CIDR 随机采样多个 IP 地址
4. **离线地理定位**：使用 ip2region xdb 数据库进行高速离线查询（~10μs/次）
5. **置信度分层**：根据采样命中率分为 high/medium/none 三个等级
6. **结果输出**：生成 txt/csv/json 三种格式的结果文件

## 核心特性

- ✅ **完全离线查询**：ip2region 本地数据库，无需在线 API
- ✅ **高性能并发**：asyncio + aiohttp 异步获取 ASN 前缀
- ✅ **大网段智能拆分**：自动将 /16~/23 大网段拆分为 /24 子网，避免大网段内混合运营商导致的采样误判
- ✅ **智能采样**：多点随机采样提升大网段识别准确率
- ✅ **结果分层**：high（全部命中）/ medium（部分命中）/ none（未命中）
- ✅ **自动缓存**：API 查询结果本地缓存，减少重复请求
- ✅ **灵活配置**：支持自定义采样数、并发数、ASN 列表

## 项目结构

```
china-mobile-ip-hebei/
├── data/                       # 数据文件目录
│   ├── cmcc.txt               # 中国移动 ASN 列表（逗号分隔）
│   ├── ip2region_v4.xdb       # ip2region 数据库（自动下载）
│   └── prefixes_cache.json    # API 查询缓存
├── output/                     # 输出结果目录
│   ├── hebei_cmcc_cidr.txt    # 河北移动 CIDR 列表（纯文本）
│   ├── hebei_cmcc_cidr.csv    # 详细分析结果（CSV 格式）
│   └── hebei_cmcc_cidr.json   # 完整数据（JSON 格式）
├── src/                        # 源代码目录
│   ├── ip2region/             # ip2region Python binding
│   ├── main.py                # 主程序入口
│   ├── ip2region_client.py    # IP 查询客户端
│   ├── fetch_prefixes_async.py # ASN 前缀获取（RIPEstat API）
│   ├── scanner_advanced.py    # CIDR 扫描器
│   └── ...                    # 其他工具模块
├── requirements.txt           # Python 依赖
└── README.md                  # 本文档
```

## 快速开始

### 1. 环境准备

```bash
# 克隆仓库
git clone https://github.com/yourusername/china-mobile-ip-hebei.git
cd china-mobile-ip-hebei

# 创建虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 运行扫描

```bash
# 基础运行（使用默认参数）
python3 src/main.py

# 自定义参数运行
python3 src/main.py \
  --cmcc data/cmcc.txt \      # ASN 列表文件
  --sample 3 \                # 每个 CIDR 采样 3 个 IP
  --scan-workers 24 \         # 扫描线程数
  --fetch-concurrency 20 \    # API 并发数
  --use-cache                 # 使用本地缓存
```

### 3. 查看结果

```bash
# 查看合并后的 CIDR 列表（推荐，精简版）
cat output/hebei_cmcc_cidr_merged.txt

# 查看原始 CIDR 列表（完整版）
cat output/hebei_cmcc_cidr.txt

# 查看合并分析报告
python3 src/analyze_merge.py

# 查看详细 CSV
head output/hebei_cmcc_cidr.csv

# 查看完整 JSON
python3 -m json.tool output/hebei_cmcc_cidr.json | less
```

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--cmcc` | `data/cmcc.txt` | 中国移动 ASN 列表文件路径 |
| `--sample` | `3` | 每个 CIDR 随机采样的 IP 数量 |
| `--scan-workers` | `24` | 扫描线程池大小 |
| `--fetch-concurrency` | `20` | API 并发请求数 |
| `--use-cache` | `False` | 是否使用本地缓存（加 --use-cache 启用） |
| `--no-merge` | `False` | 禁用 CIDR 自动合并（加 --no-merge 禁用） |

## 输出文件格式

### 1. hebei_cmcc_cidr.txt（原始版）
纯文本格式，每行一个 CIDR，包含 high 和 medium 等级的结果：
```
111.11.0.0/24
111.11.1.0/24
111.11.2.0/24
...
```
📝 **特点**：保留所有原始扫描结果，适合详细分析

### 1.1 hebei_cmcc_cidr_merged.txt（合并版）⭐ 推荐
经过智能合并的精简版，将连续地址段合并成更大网段：
```
111.11.0.0/17
183.196.0.0/14
...
```
📝 **特点**：
- 自动合并连续的小网段（如多个 /24 合并为 /21）
- 大幅减少行数（通常减少 90%+）
- 保持相同的IP覆盖范围
- 更易阅读和使用

### 2. hebei_cmcc_cidr.csv
CSV 格式，包含详细分析信息：
```csv
cidr,status,hits,samples,sampled_ips
111.11.0.0/17,high,3,3,111.11.0.1|111.11.32.128|111.11.64.200
111.11.0.0/24,high,3,3,111.11.0.50|111.11.0.150|111.11.0.250
...
```

### 3. hebei_cmcc_cidr.json
JSON 格式，完整数据结构：
```json
[
  {
    "cidr": "111.11.0.0/17",
    "status": "high",
    "hits": 3,
    "samples": 3,
    "sampled": ["111.11.0.1", "111.11.32.128", "111.11.64.200"]
  },
  ...
]
```

## CIDR 智能合并

项目自动将扫描结果中的小网段合并成大网段，大幅提升可读性：

### 合并算法
1. **标准合并**：使用 `ipaddress.collapse_addresses()` 合并重叠和相邻网段
2. **超网合并**：递归尝试将相邻的同等级网段合并为更大的超网
3. **最优化**：在保持IP覆盖范围的前提下，最小化CIDR数量

### 合并效果示例
```
合并前（8个 /24）:          合并后（1个 /21）:
111.11.0.0/24              111.11.0.0/21
111.11.1.0/24                 ↓
111.11.2.0/24              覆盖相同的2048个IP
111.11.3.0/24              但只需要1行！
111.11.4.0/24
111.11.5.0/24
111.11.6.0/24
111.11.7.0/24
```

### 实际数据
基于河北移动实际扫描数据（启用大网段拆分）：
- **API 原始返回**：27,323 个网段（含大量 /16~/19 大段）
- **拆分后扫描**：148,210 个 /24 子网
- **识别河北移动**：2,604 个网段（IP 覆盖 666,624）
- **智能合并后**：211 个网段（**减少 91.9%**）
- **准确性**：✓ IP 覆盖完全一致（无损合并）

## 技术架构

### ip2region v3.x
- **版本兼容**：支持 IPv4 和 IPv6
- **三级缓存**：file / vectorIndex / content
- **查询性能**：vectorIndex 模式下 ~10μs/次
- **数据格式**：国家|省份|城市|ISP（如：中国|河北省|石家庄市|移动）

### RIPEstat API
- **端点**：`https://stat.ripe.net/data/announced-prefixes/data.json`
- **认证**：无需认证，公开访问
- **限制**：建议并发 ≤20，合理使用
- **返回**：JSON 格式，包含 IPv4/IPv6 前缀列表

### 大网段拆分算法
```python
# 问题：大网段（如 /16）内部可能混合多个运营商/地区
# 解决：拆分为 /24 子网，提高采样准确性

def split_large_prefixes(prefixes, max_prefixlen=24):
    for cidr in prefixes:
        network = IPv4Network(cidr)
        if network.prefixlen < 24:
            # 拆分成 /24 子网
            subnets = network.subnets(new_prefix=24)
            # 例如：10.0.0.0/16 → 256 个 10.0.x.0/24
        else:
            # 已经是 /24 或更小，保持不变

# 效果：
# - 原始 API 返回 27,000 个网段（含大量 /16、/17）
# - 拆分后生成 148,210 个 /24 网段
# - 识别准确率提升 3.4 倍（760 → 2,604 个河北移动网段）
```

### 采样算法
```python
# 对每个 CIDR 随机采样 n 个 IP
samples = random_sample(cidr, n=3)

# 查询每个 IP 的地理位置
for ip in samples:
    region = ip2region.search(ip)  # 格式: 国家|省份|城市|ISP
    
# 根据命中率分层
if hits == samples: status = 'high'      # 100% 命中
elif hits > 0:      status = 'medium'    # 部分命中
else:               status = 'none'      # 未命中
```

## 自定义使用场景

### 场景 1：识别其他省份
修改 `src/ip2region_client.py` 中的判断逻辑：
```python
def is_target_region(self, ip, province='河北', isp='移动'):
    region = self.search(ip)
    parts = region.split('|')
    return province in parts[1] and isp in parts[3]
```

### 场景 2：自定义 ASN 列表
编辑 `data/cmcc.txt`，添加或删除 ASN：
```
9808,56048,24400,56040,56046,...
```

### 场景 3：调整采样策略
```bash
# 高精度扫描（采样 10 个 IP）
python3 src/main.py --sample 10

# 快速扫描（采样 1 个 IP）
python3 src/main.py --sample 1
```

## 依赖说明

```txt
aiohttp>=3.8.0      # 异步 HTTP 客户端
tqdm>=4.65.0        # 进度条显示
requests>=2.28.0    # HTTP 请求库
```

Python 版本要求：`>= 3.8`

## 性能指标

基于默认配置（26 个 ASN，采样 3 次）：

- **ASN 前缀获取**：~30 秒（首次，含 API 请求）
- **大网段拆分**：~5 秒（11,240 个大网段 → 377,593 个 /24 子网）
- **CIDR 扫描**：~3 分钟（扫描 148,210 个 /24 网段，8 线程）
- **结果合并**：<1 秒（2,604 → 211 个网段）
- **总耗时**：~4 分钟（首次运行）
- **缓存加速**：~3 分钟（使用 --use-cache）

**准确性提升**：
- 优化前：识别 760 个河北移动网段
- 优化后：识别 2,604 个河北移动网段（**提升 3.4 倍**）

## 常见问题

### Q1: ip2region_v4.xdb 下载失败？
**A**: 手动下载后放到 `data/` 目录：
```bash
curl -L -o data/ip2region_v4.xdb \
  https://raw.githubusercontent.com/lionsoul2014/ip2region/master/data/ip2region_v4.xdb
```

### Q2: RIPEstat API 请求失败？
**A**: 检查网络连接，或降低并发数：
```bash
python3 src/main.py --fetch-concurrency 5
```

### Q3: 如何更新 ip2region 数据库？
**A**: 删除旧文件后重新运行：
```bash
rm data/ip2region_v4.xdb
python3 src/main.py
```

### Q4: 输出结果为空？
**A**: 检查 ASN 列表是否正确，或查看 `prefixes_cache.json` 是否有数据。

## 参考资料

- [ip2region 官方仓库](https://github.com/lionsoul2014/ip2region)
- [RIPEstat API 文档](https://stat.ripe.net/docs/data_api)
- [ip2region Python Binding](https://github.com/lionsoul2014/ip2region/tree/master/binding/python)

## 许可证

本项目遵循 [LICENSE](LICENSE) 文件中的许可协议。

---

<!-- STATS_START -->

## 按省份统计（自动生成）

| 省份 | 命中 IP 段数 |
|------|------------:|
| 河北 | 3436 |
| 江西 | 59 |
| 天津 | 29 |
| 湖北 | 4 |
| 西藏自治区 | 2 |
| 山西 | 2 |
| 广东 | 1 |
| 浙江 | 1 |
| 北京 | 1 |
| 湖南 | 1 |
| 福建 | 1 |
| 云南 | 1 |
| 新疆维吾尔自治区 | 1 |
| 河南 | 1 |
| 江苏 | 1 |
| 宁夏回族自治区 | 1 |

<!-- STATS_END -->
