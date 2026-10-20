---
applyTo: 'thesis/**,docs/**'
description: 'Pre-LLM academic thesis writing style, tone, and section templates modeled on 2024____JupyRecSys_Ouyu_Selin.pdf and docs/status/THESIS_WRITING_GUIDE.md.'
---

# Thesis Writing Instructions

Follow [THESIS_WRITING_GUIDE.md](../../docs/status/THESIS_WRITING_GUIDE.md) whenever structuring, drafting, or revising the master's thesis (`thesis/**`) or thesis-facing documentation (`docs/**`).

## Core Principles

- **Pre-LLM human academic quality:** Write clear, logically coherent, connected paragraphs that read naturally from section to section. Keep chapters compact and informative. Never use AI filler words (*"delve"*, *"tapestry"*, *"leveraging"*, *"paradigm shift"*, *"holistic"*), inflated vocabulary, or disconnected bullet dumps.
- **Direct, explanatory `"we"` voice:** State the purpose and reason for every design decision before introducing the technical mechanism (*"We have chosen X because we want to analyze Y"*, *"In order to further reduce X and get more accurate results, we also..."*).
- **Concrete task examples before internal names:** Introduce every concept, metric, or failure mode through a concrete school-math task example before naming stages or metrics. Keep internal code identifiers, JSON schema keys, and file paths out of the main thesis prose.
- **No `\paragraph{Title.}` run-in headers with periods:** For paragraph lead-ins, use `\textbf{Title:}` (with a colon and normal space) or a numbered list (`1. \textbf{Title}\\[0.2em] Paragraph...`), never `\paragraph{Title.}`. Reserve detailed per-cell and sample-size breakdowns for tables while prose states only the headline takeaway.
- **No em-dashes (`—` or `---`):** Never use the em-dash symbol (`—` or LaTeX `---`) in thesis prose, captions, tables, or figures. Use commas, parentheses, colons, or separate sentences instead.
- **Short noun/gerund section titles:** Keep chapter, section, and subsection titles concise and nominal (e.g., *"Need for External Curriculum Grounding"*, *"Selecting and Verifying Task Numbers"*), never full sentences or questions.

## Section Templates (from `JupyRecSys`)

1. **Introduction:** Open with a practical observation, state the gap, explain in two plain sentences why the simple baseline falls short (*"While X could be employed for this purpose, ... The success is dependent on ... An alternative approach would be..."*), and conclude with crisp, single-sentence numbered goals (`G1–G3` or `RQ1–RQ3`).
2. **Related Work:** For each prior system or method, explain how its mechanism works in 3–4 sentences, state its practical limitation (*"However, ... Additionally, ..."*), and end the section with a short synthesis paragraph contrasting them (*"While System A offers..., in contrast, System B..."*) to motivate our approach.
3. **Method Subsections:** Open with 1–2 sentences explaining what problem the step solves and why, pair it with a clean left-to-right process diagram (`Fig. 1, Fig. 2, ...`), and walk through the diagram linearly (*"An illustration of the entire process is shown in Figure X. Every single item undergoes this process, which has two parts. First, ... The second part entails ... Finally, ..."*).
4. **Evaluation & Results:** First explain *why* the evaluation dataset is constructed the way it is (`Query Dataset` / `Evaluation Setup`). After presenting the results table, explain the mathematical or structural reason why the metrics behave as observed, and contrast concrete high-scoring cases against concrete low-scoring cases to explain why the difficult cases failed.

## Figure & Diagram Style (ETH LRE Lab: *MathDial* & *StratL*)

Follow the visual conventions from Jakub Macina and Prof. Mrinmaya Sachan's papers (*MathDial* 2023, *StratL* 2025), implemented in [plot_eth_style_samples.py](../../scripts/plot_eth_style_samples.py):
- **Pipeline Diagrams:** Use light dashed rounded stage containers (`#FAFAFA` fill, `#888888` border) with semantic `draw.io` pastel inner boxes (`#DAE8FC` blue input, `#FFF2CC` yellow LLM step, `#D5E8D4` green verified check, `#F8CECC` red blocked spoiler) and an embedded worked math example (`✓` / `✗`). Sample: [eth_sample_1_structpf_diagram.png](../../docs/status/figures/eth_samples/eth_sample_1_structpf_diagram.png) ([PDF](../../docs/status/figures/eth_samples/eth_sample_1_structpf_diagram.pdf)).
- **Quantitative Charts:** Use the multi-hue academic palette (`#C44E52` muted red, `#DD8452` warm orange, `#55A868` sage green, `#4C72B0` steel blue) with open top/right spines, light dashed gridlines, direct bar value annotations, and a framed legend above the axes. Samples: [eth_sample_2_grounding_3arms.png](../../docs/status/figures/eth_samples/eth_sample_2_grounding_3arms.png) ([PDF](../../docs/status/figures/eth_samples/eth_sample_2_grounding_3arms.pdf)) and [eth_sample_3_solver_recall.png](../../docs/status/figures/eth_samples/eth_sample_3_solver_recall.png) ([PDF](../../docs/status/figures/eth_samples/eth_sample_3_solver_recall.pdf)).
