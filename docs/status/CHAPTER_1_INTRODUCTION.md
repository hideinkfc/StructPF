# Chapter 1: Introduction — Direction and Draft Outline (`JupyRecSys` Style)

Add your comments or adjustments directly under any paragraph block below.

---

## Paragraph 1 — What Productive Failure Is and What Good Effect It Has
- **Direction:** Introduce PF simply (inverting standard instruction into an exploration phase followed by consolidation) and state its positive effect on deep understanding in plain language, without heavy academic jargon or long posttest details.
- **Draft flow (`JupyRecSys` tone):**
  > In traditional mathematics instruction, teachers first explain a new concept and its formula, and students then practice applying it on routine exercises. Productive Failure (PF) reverses this order by dividing learning into two phases (`Kapur, 2008`; `Kapur & Bielaczyc, 2012`). In the first phase, students work on a challenging, uninstructed problem using only the mathematical methods they already know, generating multiple representations and solution attempts. In the second phase, the teacher compares the students' attempts with the target method to show why the new concept is needed. Even though students usually fail to find the canonical formula on their own in the first phase, trying out their existing methods helps them notice the exact gap in their current knowledge, which prepares them to understand the new concept much more deeply and transfer it to new problems (`Kapur, 2012`; `Loibl & Rummel, 2014`; `Sinha & Kapur, 2021`).

<!-- Comment on Paragraph 1 here -->


---

## Paragraph 2 — Why PF Tasks Are Hard and Time-Consuming for Teachers to Design in Practice
- **Direction:** Explain why teachers struggle to design PF tasks in everyday practice (`Kapur & Bielaczyc, 2012`): finding the "sweet spot" of difficulty, tuning the numbers so familiar methods fail on the key feature, and avoiding hints—which currently requires slow manual trial-and-error.
- **Draft flow (`JupyRecSys` tone):**
  > Despite these benefits, Productive Failure is still difficult to use regularly in classrooms because designing a working PF problem requires significant time and effort from teachers (`Kapur & Bielaczyc, 2012`). Unlike a standard textbook exercise that simply asks students to apply a taught formula, a PF task must balance three requirements at the same time. First, the problem must sit in a "sweet spot" where students can easily start using familiar methods without becoming frustrated and giving up. Second, the numbers and conditions in the problem must be carefully chosen so that those familiar methods break down on the specific feature of the new concept—for example, choosing speed ratios where simple proportional reasoning fails, or datasets where familiar averages give the same result (`Kapur & Bielaczyc, 2012`; `Loibl & Rummel, 2014`). Third, the task prompt must stay open-ended without giving away procedural hints, which goes against how teachers and textbooks usually guide students. In practice, finding numbers and wording that satisfy all three requirements requires multiple rounds of manual design and pilot testing.

<!-- Comment on Paragraph 2 here -->


---

## Paragraph 3 — The AI Part: Why One-Shot LLMs and Surface Judges Fall Short, and Our Alternative
- **Direction:** Follow the `JupyRecSys` transition (*"While X could be employed for this purpose... An alternative approach would be..."*) to move from the teacher bottleneck to LLMs, state why one-shot prompting and surface rubric scoring fail, and introduce `StructPF` and our Principle-Based Evaluator.
- **Draft flow (`JupyRecSys` tone):**
  > Large Language Models (LLMs) offer a promising way to reduce this design effort by automatically generating PF problems for a given mathematics topic (`Rahimi et al., 2025`; `Puech et al., 2025`). While one-shot prompting could be employed for this purpose, its success is limited by how instruction-tuned LLMs behave. Without clear curriculum boundaries and numerical checks, an LLM asked to write a PF task often creates a routine story problem that students can already solve with familiar math, or acts like a helpful tutor and guides the student step by step toward the target formula. Evaluating these generated problems is a second challenge: standard LLM rubric judges only read the surface text of the task, rewarding fluent stories and open-sounding wording with high scores even when the numbers contain no productive trap. An alternative approach is to break task generation into structured stages—grounding prior skills in a curriculum graph and verifying the numerical trap with a calculator before writing the problem text (`StructPF`)—and to evaluate generated tasks by testing whether a solver restricted to prior knowledge actually fails in the intended way.

<!-- Comment on Paragraph 3 here -->


---

## Paragraph 4 — Research Goals (`G1–G4`) and Thesis Structure
- **Direction:** State the crisp single-sentence goals (`G1–G4`) and the chapter outline, matching `JupyRecSys` Section I.
- **Draft flow (`JupyRecSys` tone):**
  > The research presented in this thesis is based on the aforementioned points and aims to address the following goals:
  > - **G1:** Replicate one-shot LLM generation for Productive Failure and identify the failure modes in both generated tasks and surface rubric evaluations.
  > - **G2:** Design `StructPF`, a three-stage generation pipeline that grounds prior skills in a curriculum knowledge graph, verifies numerical traps with a calculator, and writes open student tasks without spoilers.
  > - **G3:** Develop and validate a principle-based evaluation framework that tests PF tasks using a prior-knowledge-constrained solver and structural checks.
  > - **G4:** Evaluate the effect of decomposition and curriculum grounding across 30 mathematics progression topics, and analyze why alternative signals such as multiple-choice error logs and simulated-student feedback loops fall short.
  >
  > The remainder of this thesis is structured as follows: Chapter 2 reviews the background on Productive Failure and LLMs in education. Chapter 3 replicates prior one-shot PF generation and summarizes our diagnostic observations. Chapter 4 presents the `StructPF` pipeline, while Chapter 5 introduces our evaluation framework and Chapter 6 validates it on expert and control tasks. Chapter 7 reports the main evaluation of `StructPF`, the 30-topic curriculum grounding study, and the analysis of alternative signals. Finally, Chapter 8 discusses the findings, limitations, and future work.

<!-- Comment on Paragraph 4 here -->
