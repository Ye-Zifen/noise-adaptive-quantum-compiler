# 噪声自适应量子编译器

**CCF 2026 噪声自适应量子编译挑战赛 · 算法赛道第二名。**

一个面向 NISQ 设备的量子比特映射与路由编译器。它不优化 SWAP 数、电路深度或估计对数可靠度这类
**代理指标**,而是**并行生成多种候选编译,再用对"真实带噪成功率"的廉价估计择优**——且全程不读取期望答案。

| | Track A | Track B | Final |
|---|---:|---:|---:|
| 官方 `RouteCQC` baseline | 0.7583 | 0.4062 | 0.6703 |
| **本工作**(seed 7) | **0.8647** | **0.5693** | **0.7909** |
| 本工作(10-seed 均值) | 0.8654 | 0.5684 | 0.7911 |

相对官方 baseline **提升 18.0%**,公开集 10/10 样本全部合法。模拟器是种子化的,上表数字用
[复现命令](#复现)可**逐位重现**。

[English README](README.md) · [完整方法文档 (PDF)](submission/docs/solution_zh.pdf)

---

## 赛题

编译器作为黑盒命令被调用:

```bash
compiler --circuit circuit.json --backend backend.json --out compiled_circuit.json
```

需把逻辑线路映射到含噪后端的物理比特与耦合图上,输出 Cirq JSON 线路加 layout sidecar,通过隐藏的
无噪等价性检查,然后在"两比特门 depolarizing + 读出 bit-flip"的噪声模型下按
`success_rate = correct_shots / total_shots` 打分。Track A 是 Cirq 密度矩阵采样的通用线路(权重 0.75),
Track B 是 Stim 采样的大规模 Clifford 压力线路(权重 0.25)。

## 方法

![整体架构](submission/docs/figures/fig_pipeline.png)

### 一、候选生成:用组合,不押单一流水线

没有哪种策略在所有线路上都最优,因此六个生成器对每个候选初始 layout 并行跑一遍,结构校验不过的直接丢弃:

- **RouteCQC**(Cirq 的前瞻路由器),外加一个不指定初始映射的裸实例作兜底
- **可靠性加权贪心**路由(小线路),沿最可靠最短路搬运
- **可靠性加权 SABRE**,含前后向初始映射精化与(度量 × 前瞻权重 × 窗口)参数扫描
- **mirror 融合束搜索**——Track A 的主要贡献(见下)
- **拓扑感知线性合成**:GF(2) 上的 RowCol 与 **PermRowCol**,Steiner 树与区域生长均按边可靠度加权
- **辅助比特星形扇出**,用空闲比特作为根值的纯净载体,服务 GHZ 族星形映射

### 二、mirror 融合束搜索

SABRE 与 RouteCQC 都是贪心的:一次提交一个 SWAP,无法回头。束搜索在(当前映射,已执行门集合)
状态上保留最优的 100 个部分解,优化目标**与评测器的对数可靠度逐项一致**——每条边各自的 CX 代价、
单比特门代价,以及最终测量位置的读出误差。两个关键点:

- **mirror 融合**:执行 `cx(a,b)` 后顺带交换该对,等价于 `cx(b,a); cx(a,b)`,共 **2 个 CX 而非 1+3**。
  把"边执行边搬运"变成一等公民操作后,几乎所有样本的 CX 数都下降:toffoli 9→8、fredkin 14→11、
  peres 13→9、or 12→8、adder 27→23、结构化随机 34→23、parity 106→88。
- **启发式必须统计全部未执行的两比特门**,而不只是就绪的那些。否则顺序依赖链(GHZ 扇出)会让落后状态
  永远比先进状态"便宜",束搜索原地打转——我们踩过并修复了这个坑。

### 三、按真实成功率估计择优

对数可靠度假设每个物理错误都致命,但事实并非如此:parity 样本上 `exp(logrel) = 0.17`,实测成功率却是
`0.44`。差距全部来自**无害错误**,利用它是 Track B 的主要贡献:

- **Clifford 线路 → 支撑集成员概率**。Clifford 线路在 `|0…0⟩` 上的无噪输出分布均匀支撑在一个 GF(2)
  **仿射子空间**上,而比赛的三种判分规则(`bitstring`、`allowed_bitstrings`、`parity_checks`)在数学上
  **恰好就是该子空间的成员测试**。因此"带噪样本仍落在无噪支撑集内的概率"就是真实得分的
  **无规则、无偏估计**——支撑集由候选线路自身重建(256 个无噪样本做 GF(2) 消元得基底,再对 4096 个带噪
  Stim 样本查归属),从不接触期望答案,每个候选耗时毫秒级。头部候选再做一次更高精度的复估。
- **非 Clifford 线路 → Pauli 轨迹蒙特卡洛**。depolarizing 是随机 Pauli 信道,轨迹态矢模拟按分布精确。
  对 logrel 落后最优不超过 0.025 的近平局候选,用 400 条轨迹重排;读出误差解析边缘化,并通过条件于
  "至少一个故障"做方差缩减。
- **死区兜底**。两种估计都不适用时退回 logrel,且不可信候选必须以 ≥0.005 的优势才能替换可信候选。
  低于该分辨率的 logrel"改进"纯属方差——10 seed 实验表明,据此换候选净贡献为负。

一个值得提醒的细节:是否启用 Clifford 这套工具,要**按线路本身判定,而不是看后端的 basis gates**。
大后端的 basis 含 `t`/`rz`,按后端判定会让整条 Clifford 路径静默失效——这是个真实的 bug,修复它值 +0.024 Final。

所有不可信候选在入选前还必须通过内部等价性自检(Clifford 用 Stim 支撑集精确比较,其余用精确直方图)。

## 复现

需要 Python 3.11+。

```bash
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'

# 完整公开集评测 —— 预期 A=0.8647  B=0.5693  Final=0.7909
nah-evaluate-submission --root . --shots-a 256 --shots-b 1024 --seed 7 \
  --out results/my_summary.json \
  --command "$(pwd)/.venv/bin/python" "$(pwd)/submission/compiler.py"

# 官方 baseline 对比 —— 预期 Final=0.6703
nah-evaluate-submission --root . --shots-a 256 --shots-b 1024 --seed 7 \
  --out results/baseline_cqc.json \
  --command "$(pwd)/.venv/bin/python" -m noise_adaptive_hackathon.cli.run_baseline --compiler cirq_cqc
```

> 评测器会在**隔离的临时目录**里运行提交命令,所以 `--command` 里的解释器和脚本**都必须写绝对路径**;
> 否则子进程可能解析到没装依赖的系统 Python,导致所有样本判零。

Windows 用户请看 [`submission/docs/windows_setup_zh.md`](submission/docs/windows_setup_zh.md),
或直接运行 [`run_checks.bat`](run_checks.bat)(自动建环境、评测本提交与 baseline 并打印对比)。

其他入口:

```bash
PYTHONPATH=src python submission/scripts/generate_compiled_outputs.py  # 逐样本编译产物
PYTHONPATH=src python submission/scripts/test_linear_synth.py          # GF(2) 合成器回归(600×2 随机用例)
bash submission/scripts/run_public_eval.sh                             # 本提交 + 两个 baseline
python submission/scripts/analyze_results.py                           # 对比表与图表
python -m pytest -q                                                    # 官方回归测试(26 项,约 3 分钟)
```

## 仓库结构

```text
submission/              ★ 本工作
├── compiler.py              提交的黑盒编译器本体
├── scripts/                 批量编译、评测、汇总作图、回归测试
├── docs/                    方法说明(md + pdf)、Windows 运行指南、图表(含 TikZ 源码)
└── results/                 评测 JSON、消融、10-seed 稳健性、逐样本编译产物

src/ benchmarks/ backends/   赛事官方发布包(评测器、模拟器、公开 benchmark、
docs/ examples/ formats/     设备快照、baseline)—— MIT 许可,版权归 SpinQ Technology
tests/ pyproject.toml        原样附带,保证仓库开箱即可复现
```

## 结果明细

消融实验、逐样本成功率与 10-seed 稳健性数据在
[`submission/results/`](submission/results/);完整方法文档(含负结果——KAK 重合成、parity 的带辅助比特
Steiner-Gauss、Paar 式公共子表达式分解——以及局限性讨论)见
[`submission/docs/solution_zh.pdf`](submission/docs/solution_zh.pdf)。

| 阶段 | Track A | Track B | Final |
|---|---:|---:|---:|
| RouteCQC baseline | 0.758 | 0.406 | 0.670 |
| + 多候选 layout + 可靠性选择 | 0.845 | 0.443 | 0.745 |
| + 拓扑感知线性合成(GHZ) | 0.845 | 0.484 | 0.755 |
| + 可靠性加权 SABRE | 0.847 | 0.493 | 0.759 |
| + SABRE 前后向精化 | 0.853 | 0.520 | 0.769 |
| + 束搜索 / PermRowCol / 死区 | 0.854 | 0.531 | 0.774 |
| + mirror 融合 + 轨迹 MC 精排 | 0.865 | 0.531 | 0.781 |
| + 支撑集真实成功率选择 + 星形扇出 | 0.865 | 0.548 | 0.786 |
| + 扇出搜参 + 大线路束搜索扩容 | **0.865** | **0.569** | **0.791** |

## 许可与署名

本仓库采用 MIT 许可。`submission/` 为原创工作;仓库根目录的赛事发布包依其自身的 MIT 许可转发
(© 2026 SpinQ Technology),详见 [`NOTICE.md`](NOTICE.md) 与
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。

本工作借鉴的既有方法:SABRE(Li, Ding & Xie, ASPLOS'19)、Cirq `RouteCQC`,以及 CNOT 电路综合文献中的
RowCol / PermRowCol。
