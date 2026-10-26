# 作品提交说明 / Submission Instructions

## 中文版

1. 本赛题为噪声自适应量子编译赛题。参赛者需提交能够被评测器作为黑盒命令运行的编译器程序，将输入量子线路编译到给定后端上，并通过公开或隐藏 benchmark 评测。仅进行理论分析、手工说明、单独仿真计算，或未提交可运行编译器代码的作品，将无法作为完整答案参与评分。

2. 参赛者需使用 Python 3.11 或更高版本，并安装发布包中提供的 Python package。推荐在发布包根目录运行：

   ```bash
   python -m venv .venv
   . .venv/bin/activate
   python -m pip install -e '.[dev]'
   ```

3. 发布包中的 `examples/cirq_route_cqc_baseline/compiler.py` 为单次编译示例代码，用于说明线路读取、后端读取、layout 生成、routing 编译、`compiled_circuit.json` 输出和 `.layout.json` sidecar 写出流程。参赛者可在此基础上编写批量评测、参数搜索、噪声自适应优化、结果统计和作图代码。

4. 单次编译运行完成后，参赛程序需写出评测器指定的 `compiled_circuit.json`，并在同目录写出对应的 `compiled_circuit.layout.json`。完整公开集评测可通过 `nah-evaluate-submission --out <summary.json>` 生成评测 summary JSON。提交时应保留评测器生成的原始 JSON 内容和文件名；JSON 文件可按赛道、实验类型或评测轮次放入分类文件夹中。

5. 作品提交包应包含三个文件夹：`1_作品说明文档`、`2_代码脚本`、`3_评测结果`。其中 `1_作品说明文档` 需同时提交 `.md` 和 `.pdf` 版本，说明方法、运行环境、复现命令、主要结果和局限性；`2_代码脚本` 需包含可运行的编译器代码、批量评测脚本、数据读取、分析和作图代码；`3_评测结果` 需包含支撑报告结论的原始评测 JSON、公开集 summary 和必要的中间结果文件。

6. 本次比赛总分为 100 分，最终成绩由可量化评测分和综合评审分合并构成。可量化评测部分主要参考 hidden benchmark 上的完成情况、编译结果合法性、成功率表现、运行稳定性和代码可复现性；综合评审部分将考察方法创新性、算法实用性、分析合理性、结果展示质量、作品说明完整性和进一步扩展潜力。每道题在可量化评测部分中的参考占比见 [分数占比说明](scoring_weights_bilingual.md)。具体权重和细则以正式评分说明为准。

## English Version

1. This challenge is a noise-adaptive quantum compiler challenge. Participants must submit a compiler program that can be executed by the evaluator as a black-box command, compile input quantum circuits onto the given backend, and pass public or hidden benchmark evaluation. Submissions containing only theoretical discussion, manual analysis, standalone simulation, or no runnable compiler code will not be considered complete submissions.

2. Participants must use Python 3.11 or later and install the Python package provided in the release bundle. From the release root, the recommended setup is:

   ```bash
   python -m venv .venv
   . .venv/bin/activate
   python -m pip install -e '.[dev]'
   ```

3. The file `examples/cirq_route_cqc_baseline/compiler.py` provides a single-sample compilation example. It demonstrates circuit loading, backend loading, layout generation, routing, writing `compiled_circuit.json`, and writing the `.layout.json` sidecar. Participants may build on this example to implement batch evaluation, parameter search, noise-adaptive optimization, result aggregation, and plotting scripts.

4. After each single compilation run, the submitted program must write the evaluator-specified `compiled_circuit.json` file and the corresponding `compiled_circuit.layout.json` file in the same directory. Full public-set evaluation can produce a summary JSON via `nah-evaluate-submission --out <summary.json>`. When submitting, keep the original evaluator-generated JSON contents and filenames unchanged. JSON files may be organized into folders by track, experiment type, or evaluation round.

5. The submission package should contain three folders: `1_Report`, `2_Code`, and `3_Evaluation_Results`. `1_Report` must include both `.md` and `.pdf` versions describing the method, runtime environment, reproduction commands, main results, and limitations. `2_Code` must include the runnable compiler, batch evaluation scripts, data loading, analysis, and plotting code. `3_Evaluation_Results` must include the original evaluation JSON files, public-set summary files, and necessary intermediate result files that support the report conclusions.

6. The total score is 100 points. The final score will combine a quantitative evaluation component and a holistic review component. The quantitative component will mainly consider hidden benchmark completion, validity of compiled outputs, success-rate performance, runtime stability, and code reproducibility. The holistic review component will consider methodological innovation, algorithmic practicality, soundness of analysis, quality of result presentation, completeness of the submission report, and potential for further extension. For reference per-problem weights within the quantitative component, see [Score Weighting](scoring_weights_bilingual.md). Detailed weights and rubrics will follow the official scoring announcement.
