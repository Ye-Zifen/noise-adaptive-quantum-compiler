@echo off
REM ============================================================
REM  一键：建环境 + 装依赖 + 跑公开集评测（本提交 + baseline）
REM  需先安装 Python 3.11 或 3.12（勾选 Add to PATH / py launcher）
REM  双击本文件，或在 cmd 里运行： run_checks.bat
REM ============================================================
setlocal
chcp 65001 >nul
cd /d "%~dp0"

REM --- 选择 Python 解释器（优先 3.12，其次 3.11）---
set "PYEXE="
py -3.12 --version >nul 2>&1 && set "PYEXE=py -3.12"
if not defined PYEXE ( py -3.11 --version >nul 2>&1 && set "PYEXE=py -3.11" )
if not defined PYEXE (
  echo [错误] 未找到 Python 3.11/3.12。请先从 python.org 安装（勾选 Add to PATH）。
  pause & exit /b 1
)
echo 使用解释器: %PYEXE%

REM --- 建 venv（若不存在）---
if not exist ".venv\Scripts\python.exe" (
  echo 正在创建虚拟环境 .venv ...
  %PYEXE% -m venv .venv || (echo venv 创建失败 & pause & exit /b 1)
)
call ".venv\Scripts\activate.bat"

REM --- 安装依赖 ---
echo 正在安装依赖（首次较慢）...
python -m pip install --upgrade pip >nul
python -m pip install -e ".[dev]" || (echo 依赖安装失败 & pause & exit /b 1)

REM --- 1) 单样本编译（接口 + sidecar 检查）---
echo.
echo === [1/4] 单样本编译 ===
python "submission\compiler.py" --circuit benchmarks\track_a\public\track_a_001\circuit.json --backend backends\medium\medium_snapshot_a.json --out results\demo\compiled_circuit.json
if exist "results\demo\compiled_circuit.layout.json" (echo   OK: 已生成 compiled_circuit.json + layout sidecar) else (echo   [警告] 缺少 layout sidecar)

REM --- 2) 本提交完整评测 ---
echo.
echo === [2/4] 公开集评测：本提交（约 1-2 分钟）===
REM 注意：评测器在隔离临时目录里运行编译器，compiler.py 和解释器都必须用【绝对路径】(%~dp0=本文件夹)
REM 裸 python 可能被子进程解析到系统里没装 cirq 的解释器，导致全部样本 invalid、总分 0
nah-evaluate-submission --root . --shots-a 256 --shots-b 1024 --seed 7 --out results\my_summary.json --command "%~dp0.venv\Scripts\python.exe" "%~dp0submission\compiler.py"

REM --- 3) baseline 评测 ---
echo.
echo === [3/4] 公开集评测：RouteCQC baseline ===
nah-evaluate-submission --root . --shots-a 256 --shots-b 1024 --seed 7 --out results\baseline_cqc.json --command "%~dp0.venv\Scripts\python.exe" -m noise_adaptive_hackathon.cli.run_baseline --compiler cirq_cqc

REM --- 4) 打印对比 ---
echo.
echo === [4/4] 分数对比 ===
python -c "import json;m=json.load(open('results/my_summary.json',encoding='utf-8'));b=json.load(open('results/baseline_cqc.json',encoding='utf-8'));print('本提交   A=%.4f B=%.4f Final=%.4f'%(m['track_a_score'],m['track_b_score'],m['final_score']));print('baseline A=%.4f B=%.4f Final=%.4f'%(b['track_a_score'],b['track_b_score'],b['final_score']));print('全部样本合法:', all(s['valid'] for s in m['sample_results']))"

echo.
echo 完成。详细结果见 results\my_summary.json
pause
endlocal
