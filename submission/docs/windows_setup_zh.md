# 本地运行说明（Windows / cmd）

本仓库是一个**自包含、可直接运行**的比赛包：`src/`（评测器+编译器库）、`benchmarks/`、
`backends/`、`pyproject.toml` 都在，`submission/compiler.py` 是我们的提交编译器。

---

## 0. 安装 Python 3.11+（题目要求；若已有 3.11/3.12 可跳过本节）

1. 打开 https://www.python.org/downloads/ ，下载 **Python 3.12.x（或 3.11.x）Windows installer (64-bit)**。
2. 运行安装程序，**务必勾选**：
   - ✅ `Add python.exe to PATH`
   - ✅ `py launcher`（默认勾选）
3. 装完后新开一个 cmd 窗口，验证：

   ```bat
   py -3.12 --version
   ```

   能打印 `Python 3.12.x` 即成功（若你装的是 3.11 就用 `py -3.11`）。

> 如果你暂时不想装新 Python，见文末【附：用现有 3.10 运行】。

---

## 1. 进入本文件夹

在 cmd 里 `cd` 到本文件夹（把下面路径换成你电脑上 CCF2026_suanfa 的真实路径）：

```bat
cd /d "C:\你的路径\CCF2026_suanfa"
```

## 2. 建虚拟环境并安装依赖（一次性）

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

成功后命令行前面会出现 `(.venv)`。这一步会安装 cirq / stim / networkx 等所有依赖，
并注册 `nah-evaluate-submission`、`nah-run-baseline` 命令。

---

## 3. 逐项检查

> 以下命令都在**已激活 venv、且位于本文件夹根目录**下运行。

### 3.1 单样本编译（验证黑盒接口 + 产出 sidecar）

```bat
python "submission\compiler.py" --circuit benchmarks\track_a\public\track_a_001\circuit.json --backend backends\medium\medium_snapshot_a.json --out results\demo\compiled_circuit.json
```

运行后检查 `results\demo\` 下应有**两个**文件：`compiled_circuit.json` 和 `compiled_circuit.layout.json`。

### 3.2 完整公开集评测（我们的提交）

> ⚠️ 关键：评测器会在**隔离的临时目录**里运行你的编译器，所以 `--command` 里的 `compiler.py`
> **必须写绝对路径**。下面用 `%CD%`（当前目录，即本文件夹）拼成绝对路径；用相对路径会报
> `can't open file ... No such file or directory`。
>
> ⚠️ 同样关键：`--command` 里的解释器也**必须写 venv python 的绝对路径**
> （`%CD%\.venv\Scripts\python.exe`）。写裸 `python` 时，子进程可能解析到系统里
> 另一个未装 cirq 的 Python，导致所有样本报 `ModuleNotFoundError: No module named 'cirq'`、
> 全部 invalid、总分为 0。

```bat
nah-evaluate-submission --root . --shots-a 256 --shots-b 1024 --seed 7 --out results\my_summary.json --command "%CD%\.venv\Scripts\python.exe" "%CD%\submission\compiler.py"
```

耗时约 1–2 分钟。结果写入 `results\my_summary.json`。

### 3.3 官方 RouteCQC baseline（用于对比）

```bat
nah-evaluate-submission --root . --shots-a 256 --shots-b 1024 --seed 7 --out results\baseline_cqc.json --command "%CD%\.venv\Scripts\python.exe" -m noise_adaptive_hackathon.cli.run_baseline --compiler cirq_cqc
```

### 3.4 查看/对比分数

```bat
python -c "import json;d=json.load(open('results/my_summary.json',encoding='utf-8'));print('本提交  A=%.4f B=%.4f Final=%.4f'%(d['track_a_score'],d['track_b_score'],d['final_score']));[print(' ',s['benchmark_name'],round(s['success_rate'],3),'valid=',s['valid']) for s in d['sample_results']]"
python -c "import json;d=json.load(open('results/baseline_cqc.json',encoding='utf-8'));print('baseline A=%.4f B=%.4f Final=%.4f'%(d['track_a_score'],d['track_b_score'],d['final_score']))"
```

预期：本提交 seed 7 应得 **Final = 0.7909**（模拟器种子化，数值逐位确定），baseline = 0.6703，两者所有样本 `valid=True`。

### 3.5 （可选）线性合成器正确性回归

```bat
set PYTHONPATH=src
python "submission\scripts\test_linear_synth.py"
```

应打印 `OK: 600 trials x 2 orders passed`。

### 3.6 （可选）批量产出每样本编译结果 + 汇总作图

```bat
python "submission\scripts\generate_compiled_outputs.py"
python "submission\scripts\analyze_results.py"
```

### 3.7 （可选，较慢）跑仓库自带回归测试

```bat
python -m pytest -q
```

> 注意：这套测试里包含完整评测，耗时数分钟，属正常。

---

## 附：用现有 3.10 运行（不装新 Python 的临时方案）

代码本身在 3.10 上可正常运行，只是 `pyproject.toml` 的版本门限会让 `pip install -e` 报错。
绕过办法是手动装依赖并用 `PYTHONPATH`：

```bat
py -3.10 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install "cirq>=1.5" "networkx>=3.2" "numpy>=1.26" "pydantic>=1.10,<3" "stim>=1.15" "stimcirq>=1.15" "pytest>=8.4"
set PYTHONPATH=src
```

之后把上面 3.x 里的 `nah-evaluate-submission` 换成
`python -m noise_adaptive_hackathon.cli.evaluate_submission`，其余命令不变。
（每开新窗口都要重新 `.venv\Scripts\activate` 并 `set PYTHONPATH=src`。）

---

## 常见问题

- **`nah-evaluate-submission 不是内部或外部命令`**：venv 没激活，或用的是 3.10 绕过方案——改用
  `python -m noise_adaptive_hackathon.cli.evaluate_submission ...`。
- **中文路径乱码**：确保 cmd 用 UTF-8（`chcp 65001`），本说明的命令已对 JSON 读取指定 `encoding='utf-8'`。
- **内存/较慢**：Track A 用 density-matrix 仿真，16 比特线路占用稍高属正常；单条编译 ≤19 秒(parity 最长)。
