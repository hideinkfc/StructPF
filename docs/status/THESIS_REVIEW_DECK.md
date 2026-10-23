# Thesis First-Reader Review Deck

## Part 1: Revised Cards & Answers to Your Comments

### [x] Card 1: Study (b) Target-Leak Count (`5` vs. `6` for Ungrounded StructPF)
* **Location:** [07-results.tex](../../thesis/sections/07-results.tex) (Section 6.4.2, Finding 1) vs. [08-discussion.tex](../../thesis/sections/08-discussion.tex) (Section 7.1, G4)
* **Your Comment:** *"Shorter, no need to be that precise, too much parenthesis"*
* **Answer & Revised Fix (Applied in [07-results.tex](../../thesis/sections/07-results.tex)):**
  * Instead of adding parenthetical counts, we added just five words (`or proposes only unrelated skills`) so there are zero parentheses and no extra numbers, while explaining why 6 topics fail Step 1 even though 5 are target leaks:
  * **Before:** *"When the model guesses what students already know from the target topic alone, it often lists the target concept itself as a prerequisite. The task then fails before students even begin, which eliminates 17 of the 30 topics for the one-shot prompt and 6 of the 30 for ungrounded `\textsc{StructPF}`."*
  * **After:** *"When the model guesses what students already know from the target topic alone, it often lists the target concept itself as a prerequisite or proposes only unrelated skills. The task then fails before students even begin, which eliminates 17 of the 30 topics for the one-shot prompt and 6 of the 30 for ungrounded `\textsc{StructPF}`."*

---

### [x] Card 4: Judge Models in Chapters 3 and 5 (`GPT-5.6-luna`)
* **Location:** [03-oneshot-replication.tex](../../thesis/sections/03-oneshot-replication.tex) (Section 3.1.2) and [05-eval-framework.tex](../../thesis/sections/05-eval-framework.tex) (Section 5.3)
* **Your Comments:** *"What were the models?"* and *"it is the model name"* (for `GPT-5.6-luna`)
* **Answer & Applied Fix:**
  * From the saved experiment logs (`pf_rahimi_multi_theme_20261013/main_30` and `pf_newest_pipeline_rahimi_eval_optA_v31_gpt5mini_20261021`), the exact models are:
    1. **Chapter 3 Rubric Judge (2 passes, Section 3.1.2):** `GPT-5.6-luna` (at high reasoning effort).
    2. **`PF Eval` Task Judge & Attempt Judge (Section 5.3):** `GPT-5.6-luna`.
    3. **`PF Eval` Prior-Knowledge Solver (Section 5.3, 5.4.1, and 6.1):** Pooled attempts from `GPT-5.6-luna` and `GPT-4.1`.
  * We kept `GPT-5.6-luna` as the model name everywhere and added those exact model names in Section 3.1.2 ([03-oneshot-replication.tex](../../thesis/sections/03-oneshot-replication.tex)) and Section 5.3 ([05-eval-framework.tex](../../thesis/sections/05-eval-framework.tex)).

---

### [x] Card 6: Preempting the "Prompt Fairness" Question Between One-Shot and StructPF
* **Location:** [07-results.tex](../../thesis/sections/07-results.tex) (Section 6.3, right after Table 6.1)
* **Your Comment:** *"HOw to fix it?"*
* **Answer & Applied Fix (Added in [07-results.tex](../../thesis/sections/07-results.tex) right after the 80.0% vs. 10.2% sentence):**
  * We added one sentence pointing out that the one-shot prompt already includes five published PF tasks built around numerical ties and missing measurements (Table A.1), yet a single pass still fails to verify the numbers it writes:
  * **Added Sentence:** *"This gap does not arise because the one-shot prompt lacked examples of numerical ties, as its prompt already includes five published PF tasks built around tied averages and missing measurements (Table~\ref{tab:app-oneshot-prompt}), yet a single pass still fails to verify the numbers it writes."*

---

## Part 2: Directly Approved & Applied Fixes

* **[x] Card 2 (`Do this`):** Renamed `\chapter{Rubrics, Prompts, and Full Task Examples}` to `\chapter{Prompts and Evaluation Rubrics}` in [appendix-b-rubrics.tex](../../thesis/sections/appendix-b-rubrics.tex).
* **[x] Card 3 (`Delete that sentence instead of explain`):** Deleted *"Stage 1 is a database query and has no prompt."* from [appendix-b-structpf-prompts.tex](../../thesis/sections/appendix-b-structpf-prompts.tex).
* **[x] Card 5 (`Good`):** Updated the simulated-student sentence in [abstract.tex](../../thesis/abstract.tex) and added the Chapter 6 roadmap sentence in [07-results.tex](../../thesis/sections/07-results.tex) introducing Sections 6.1--6.4 and Section 6.5.
* **[x] Card 7 (`Goold`):** Added the bridge sentence in Section 6.1 ([07-results.tex](../../thesis/sections/07-results.tex)) explaining that Study (b) pairs a curriculum Prior-Knowledge Check with the solver and attempt judge of `\textsc{PF Eval}`.
* **[x] Card 8 (`put the fix`):** Added the **All 5** column to Table 6.1 and updated Failure Cause 2 in Section 6.3 ([07-results.tex](../../thesis/sections/07-results.tex)) to read *"On 21 of the 117 accessible tasks, the numbers do not make the simpler method fail..."*.
* **[x] Card 9 (`add`):** Added the group and approach counts in Section 5.4.1 ([05-eval-framework.tex](../../thesis/sections/05-eval-framework.tex)): 12 published PF tasks (28 approaches), 12 routine and control tasks (19 approaches), and 52 pipeline-generated tasks (209 approaches).
* **[x] Card 10 (`all good but no and for this feedback`):** Added *"I would also like to thank Prof.~Dr.~Mrinmaya Sachan for the opportunity to conduct this thesis in the Learning and Reasoning Lab (LRE)."* to [ack.tex](../../thesis/ack.tex).
* **[x] Card 11 (`We want TItle Case`):** Converted all figure and table captions (both short list entries and full captions) across Chapters 1--5 and Appendix A to Title Case so the entire thesis matches Chapter 6.
* **[x] Card 13 (`fix them all`):** Added `\textsc{StructPF}` in [appendix-b-structpf-prompts.tex](../../thesis/sections/appendix-b-structpf-prompts.tex), capitalized `Grade~7` and `Grade~11` across Chapters 2, 3, and Appendix A, and added trailing periods to Tables 5.1, 5.2, and 5.3 in [05-eval-framework.tex](../../thesis/sections/05-eval-framework.tex).

