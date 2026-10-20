# Master's Thesis Writing Guide: Goal, Tone, and Style

This document records the writing principles, tone, and structural templates for the ETH Master's Thesis, grounded in the author's requirements and the reference style of `2024____JupyRecSys_Ouyu_Selin.pdf`.

---

## 1. Core Goal of the Thesis

- **Pre-LLM human academic quality:** The thesis must read like a well-crafted, pre-LLM master's thesis—clear, structured, logically coherent, and natural to read from start to finish.
- **Informative and easy to follow:** Every chapter and subsection must teach the reader a clear idea, mechanism, or empirical lesson without making the reader guess how pieces connect.
- **Compact and free of fancy filler:** Keep sections concise and purposeful. Avoid inflated vocabulary, AI buzzwords (*"delve"*, *"tapestry"*, *"leveraging"*, *"paradigm shift"*, *"holistic framework"*), repetitive summaries, and disconnected bullet-point dumps.
- **Honest scientific boundaries:** Distinguish what is implemented, what is measured in computational experiments, and what requires future human or classroom validation. Report negative or null findings with the same clarity as positive results.

---

## 2. Tone and Voice

- **Direct, explanatory `"we"` voice:** Write in natural academic `"we"` prose where every design choice is immediately justified by its purpose (*"We have chosen X because we want to analyze Y"*, *"In order to reduce X and obtain more accurate results, we also..."*).
- **Connected paragraphs over fragments:** Explain how ideas relate in flowing sentences rather than chopping explanations into telegraph-style labels or bullet fragments. Reserve bullet lists for genuinely discrete enumerations (such as numbered research goals `G1–G3` or research questions).
- **Plain English before internal terminology:** Start every concept or failure mode with what happens in the student's mathematical task (for example, comparing two rental plans or sharing cakes across tables) before introducing stage names, prompt roles, or metric identifiers. Keep raw JSON keys, file paths, and prompt payloads out of the main narrative (or in the appendix).
- **No em-dashes (`—` or `---`) and no sentence titles:** Never use the em-dash (`—` or LaTeX `---`) anywhere in the thesis prose, tables, captions, or figures; use commas, parentheses, colons, or separate sentences instead. Keep section and subsection titles as compact noun or gerund phrases rather than full sentences or questions.

---

## 3. Structural Patterns by Section (from `JupyRecSys`)

### 3.1 Introduction: Practical Problem $\to$ Baseline Limitation $\to$ Numbered Goals (`G1–G3`)

Open with a concrete observation about real educational or engineering practice, state the gap, explain in two plain sentences why the obvious baseline (e.g., one-shot direct prompting or surface rubric scoring) falls short, and finish with crisp, one-sentence goals.

> **Reference example (`JupyRecSys`, Section I):**
> *"One initial challenge is to identify and find relevant code from previous Notebooks. While search systems could be employed for this purpose, they require manual operation by the developer. The success of the search is dependent on the keywords used. An alternative approach would be to utilize a recommender, which would suggest relevant cells from previous Notebooks to match the cell currently being worked on. This would significantly reduce the required effort, as no action would be required from the developer."*
>
> *"The research presented in this paper is based on the aforementioned points and aims to address the following goals:*
> *G1: Design a recommender system algorithm that, given a cell, recommends similar cells...*
> *G2: Provide a user-friendly Jupyter Lab extension that integrates the algorithm...*
> *G3: Provide a framework for automatic evaluation..."*

---

### 3.2 Related Work: Mechanism $\to$ Practical Limitation $\to$ Side-by-Side Synthesis

For each prior work or baseline, spend 3–4 sentences explaining *how its mechanism works*, immediately state its *practical limitation* (*"However, ... Additionally, ..."*), and close the section with a synthesis paragraph (*"While System A offers..., its complexity... In contrast, System B..."*) that directly motivates our approach.

> **Reference example (`JupyRecSys`, Section II):**
> *"The recommendation of similar Notebooks is based on a two-stage process. The initial stage involves subgraph matching to identify structurally similar Notebooks, while the second stage entails a detailed similarity computation of each node. The system is demonstrated to be effective in identifying the most similar Notebooks based on user queries. However, Jupysim is currently only available as a separate web interface, suggesting the potential for a more integrated Jupyter Lab solution. Additionally, its complex, detailed graph-based query construction may impede user adoption for regular Notebook reuse."*
>
> *"While JupySim offers a sophisticated graph-based approach to identifying similar Notebooks, its complexity and standalone nature may not be optimal for everyday use. In contrast, Elyra, with its integrated Jupyter Lab interface, streamlines code snippet reuse but necessitates manual labeling and does not support the reuse of entire Notebooks."*

---

### 3.3 Method Subsections: Purpose (`"because..."`) $\to$ Process Diagram $\to$ Step-by-Step Walkthrough

Every method subsection should:
1. Open with 1–2 sentences stating **what problem this step solves and why** (*"To make recommendations from a database, we need to... We have chosen X because..."*).
2. Include a clean left-to-right block diagram (`Fig. 1, Fig. 2, ...`) showing the inputs, transformations, and outputs.
3. Walk the reader through the diagram in order using clear signposts (*"An illustration of the entire process is shown in Figure 2. Every single cell undergoes this process, which has two parts. First, ... The second part of the process entails ... Finally, ..."*).

> **Reference example (`JupyRecSys`, Section III-B):**
> *"To make recommendations from a database, we need to efficiently store existing notebooks and their cells in one place. The goal is to save storage space and optimize retrieval of this data. We also need to consider how to represent the data so that a recommender algorithm can work as efficiently as possible. We have chosen a cell representation in a vector space because we want to analyze similarities. This would mean that items that are particularly close in the vector space are particularly similar. In order to further reduce the search space and get more accurate results, we also label each cell representation with the activity it is performing, i.e. preprocessing, model building, evaluation, etc."*
>
> *"An illustration of the entire process is shown in Figure 2. Every single cell undergoes this process, which has two parts. First, the code in the cells is broken down into its components... The second part of the process entails the labeling of each cell with the specific activity being performed... Finally, the generated label for each cell is attached to its representation in the vector space, resulting in a labeled cell embedding."*

---

### 3.4 Evaluation & Results: Dataset Logic $\to$ Headline Table $\to$ Mechanism Behind the Numbers $\to$ Best vs. Worst Cases

1. **Explain why the test dataset is constructed the way it is** before presenting any numbers (`Query Dataset`, `Evaluation Setup`), walking through how a single topic or case is turned into evaluation inputs.
2. **Present the headline table and explain *why* the metrics behave that way mathematically** (for example, explaining numerator/denominator relationships or gate dependencies rather than merely reading numbers off the table).
3. **Contrast concrete high-scoring cases against low-scoring cases** (by case ID or topic) and explain the exact structural reason why the hard cases failed.

> **Reference example (`JupyRecSys`, Section V-C):**
> *"The overall mean accuracy scores are depicted in Table I. The overall mean Precision@3, Recall@3, and F1@3 scores are all identical, with a value of 0.8697. This consistency can be attributed to the specific characteristics of the evaluation setup. Each recommendation list contains three cells (the top three recommendations), and the number of relevant cells is three for all queries, as there are three mutations created for all original query cells. This results in the same denominator for the metrics Precision@3 and Recall@3. They also share the same numerator of true positives (TP), which are the relevant cells in a recommendation list."*
>
> *"The cells with the highest nDCG@3 scores, such as those with IDs 48, 70, and 103, achieved perfect scores across all metrics... The code of these cells is minimal, consisting of only one line... In contrast, the cells with the lowest nDCG@3 scores, such as those with IDs 40, 4, and 76, contain more lines of code and multiple tasks, including an import of dependencies and an additional preprocessing step in one cell... However, the versions of the original cells with fewer lines may sometimes exhibit a higher degree of similarity with recommendation cells with fewer lines than with the most relevant recommendation cell, which contains more lines. This phenomenon can lead to the erroneous recommendation of cells with fewer lines, which in turn lowers the average accuracy for the specific original cell."*

---

## 4. Figure and Diagram Style (ETH LRE Lab: *MathDial* & *StratL*)

All thesis figures and diagrams follow the publication style of Jakub Macina and Prof. Mrinmaya Sachan's ETH LRE papers (*MathDial*, EMNLP Findings 2023; *StratL*, AIED 2025), implemented in [plot_eth_style_samples.py](../../scripts/plot_eth_style_samples.py):

- **Pipeline and Architecture Diagrams (*MathDial* Fig. 2 / *StratL* Fig. 1 style):**
  - Group pipeline stages inside light dashed rounded containers (`#FAFAFA` fill, `#888888` dashed border) with bold numbered stage titles (`1. ...`, `2. ...`, `3. ...`).
  - Use semantic `draw.io` pastel fills with darker matching borders rather than monochrome blue:
    - **Curriculum / Input data:** Pastel Blue (`#DAE8FC` fill, `#6C8EBF` border)
    - **LLM Generation / Reasoning step:** Pastel Yellow (`#FFF2CC` fill, `#D6B656` border)
    - **Verified / Grounded state or check:** Pastel Green (`#D5E8D4` fill, `#82B366` border)
    - **Blocked Spoiler / Error state:** Pastel Red (`#F8CECC` fill, `#B85450` border)
  - Embed a concrete worked school-math snippet inside the diagram (with `✓` and `✗` markers) so the reader sees how a real topic flows through the stages without reading a wall of text.
  - **Reference sample:** [eth_sample_1_structpf_diagram.png](./figures/eth_samples/eth_sample_1_structpf_diagram.png) ([PDF](./figures/eth_samples/eth_sample_1_structpf_diagram.pdf))

- **Quantitative Plots and Evaluation Charts (*MathDial* Fig. 3 & Fig. 5 / *StratL* Fig. 3 style):**
  - Use a multi-hue academic publication palette (Seaborn `deep` / `colorblind` family) with thin dark borders (`#333333`):
    - **Muted Red (`#C44E52`):** Invalid / Spoiler / Failed state (e.g., Score 0)
    - **Warm Orange (`#DD8452`):** Partial / Baseline / Single-model comparison (e.g., Score 1 or Model B)
    - **Sage Green (`#55A868`):** Productive / Verified / Combined union (e.g., Score 2 or Two-Solver Union)
    - **Steel Blue (`#4C72B0`):** Primary reference model or baseline series (e.g., GPT-4.1)
  - Hide top and right axes spines (`ax.spines["top"].set_visible(False)`, `ax.spines["right"].set_visible(False)`), use subtle dashed gridlines (`#D8D8D8`, `linestyle="--"`) behind bars, print direct percentage/count labels on or above bars, and place a framed legend centered above the plot (`bbox_to_anchor=(0.5, 1.03)`).
  - Export every figure as vector `.pdf` (`pdf.fonttype = 42` for editable LaTeX inclusion) alongside a `300 DPI` `.png` preview.
  - **Reference samples:**
    - Horizontal stacked bar chart (30-topic, 3-arm curriculum grounding): [eth_sample_2_grounding_3arms.png](./figures/eth_samples/eth_sample_2_grounding_3arms.png) ([PDF](./figures/eth_samples/eth_sample_2_grounding_3arms.pdf))
    - Grouped vertical bar chart (76-task, 256-approach solver recall): [eth_sample_3_solver_recall.png](./figures/eth_samples/eth_sample_3_solver_recall.png) ([PDF](./figures/eth_samples/eth_sample_3_solver_recall.pdf))

---

## 5. Checklist Before Finalizing Any Thesis Section

1. **Does the opening paragraph state the practical problem and why the step is needed in plain English?**
2. **Are all design choices justified with `"because..."` or `"in order to..."` before naming technical components?**
3. **Does every process diagram follow the ETH LRE (*MathDial* / *StratL*) style and have a matching `"First... Second... Finally..."` prose walkthrough?**
4. **Are internal code identifiers, JSON keys, and prompt engineering jargon kept out of the main prose?**
5. **After every results table or chart, do we explain *why* the numbers behave that way and contrast concrete success cases with concrete failure cases?**
6. **Is the prose free of AI filler words and disconnected bullet fragments?**
