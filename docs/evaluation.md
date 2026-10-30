# Evaluation Plan and Measured Results

Objective 3 of the project is *"to evaluate the system's usability, performance and effectiveness
in reducing administrative workload through user testing with administrators, teachers and
students."* This document specifies the instruments, the protocol and what has already been
measured. Sections marked **To be completed with participants** are protocols, not results —
no participant data has been collected yet and none is invented here.

---

## 1. Evaluation questions

| ID | Question | Instrument |
| --- | --- | --- |
| EQ1 | Is the system usable by administrators, teachers and students without training? | Task-based usability test + SUS-10 |
| EQ2 | Does the system respond fast enough for daily classroom and office use? | `seed/bench.py` endpoint benchmark |
| EQ3 | Does the system reduce the administrative workload of preparing academic reports? | Before/after time-on-task comparison |
| EQ4 | Can teachers identify at-risk students earlier and more consistently with the dashboard? | Flag-vs-judgement agreement study |
| EQ5 | Is the data consistent and access correctly restricted? | Automated verification suite |

---

## 2. Design

A mixed-method, single-group evaluation:

1. **Technical verification** (no participants) — automated functional and performance tests. Done.
2. **Task-based usability sessions** — 3 administrators, 6 teachers, 15 students, each performing
   realistic tasks with think-aloud, then completing SUS-10.
3. **Workload comparison** — the same report-preparation task executed with the existing
   spreadsheet workflow and with the system; elapsed time and error count compared per participant.
4. **Risk-identification study** — teachers review one class and mark students they consider
   at risk; their judgement is compared with the system's 高风险/中风险 flags produced from the
   same exam data.

---

## 3. Performance — measured

Environment: Windows, single uvicorn worker, SQLite, 480 students / 24 classes / 7200 grades /
9600 attendance rows (≈1.6 MB database). Command: `python -m seed.bench`.

| Endpoint | n | Mean | P50 | P95 | Max | Payload |
| --- | --- | --- | --- | --- | --- | --- |
| GET /healthz | 30 | 1.2 ms | 1 ms | 2 ms | 2 ms | 0.0 KB |
| GET /welcome (dashboard) | 30 | 3.4 ms | 3 ms | 5 ms | 5 ms | 3.0 KB |
| POST /api/student/list | 30 | 2.2 ms | 2 ms | 3 ms | 3 ms | 2.0 KB |
| POST /api/tongji/bj_list | 30 | 3.9 ms | 4 ms | 5 ms | 5 ms | 8.0 KB |
| POST /api/tongji/chart | 30 | 5.1 ms | 5 ms | 6 ms | 6 ms | 3.7 KB |
| POST /api/risk/list (all 480 students) | 20 | 37.4 ms | 31 ms | 69 ms | 69 ms | 121 KB |
| POST /api/risk/chart | 20 | 30.2 ms | 24 ms | 62 ms | 65 ms | 1.0 KB |
| GET /report/banji (printable report) | 20 | 11.8 ms | 12 ms | 13 ms | 16 ms | 12 KB |
| GET /api/report/all.xlsx (24 classes) | 10 | 330.1 ms | 316 ms | 360 ms | 360 ms | 55 KB |

Interpretation:

- All interactive read paths answer in **single-digit milliseconds at P50** and below 70 ms at P95,
  i.e. well under the 100 ms "instantaneous" threshold used in interaction design.
- The whole-school risk computation is the heaviest read path (480 students × 6 subjects, plus
  attendance aggregation) but stays at **31 ms P50 / 69 ms P95**.
- Batch report generation is the only operation above 100 ms (**316 ms P50**) because it builds
  25 worksheets in one file. It is a back-office, one-click operation, so this is acceptable;
  optimising it (single pass over grades instead of per-class queries) is recorded as future work.

Functional verification (all executed, see `seed/check*.py`):

| Script | Scope | Result |
| --- | --- | --- |
| `check.py` | statistics cross-validation, exam numbers, grade write-back, charts, permissions, student portal | 40 / 40 pass |
| `check_teaching.py` | courses, enrolment, attendance, risk dashboard, reports, RBAC boundaries | 34 / 34 pass |
| `check_pages.py` | server-side rendering of 28 pages | 28 / 28 pass |
| `check_crud.py` | create → list → update → delete on generic modules | 0 failures |
| `check_io.py` | exam-number idempotency + Excel export/import round-trip | round-trip consistent |

---

## 4. Usability — SUS-10 protocol

**Participants.** Administrators (n = 3), teachers (n = 6), students (n = 15). Recruited from one
school; no prior exposure to the system.

**Procedure (≈25 min per participant).**

1. 5 min: briefing, consent, no training beyond the login credentials.
2. 15 min: think-aloud completion of the role-specific task list below; the moderator records
   completion, time and errors but does not help unless the participant is blocked for > 2 min.
3. 5 min: SUS-10 questionnaire, then a short semi-structured interview.

**Task list (role-specific).**

| # | Role | Task |
| --- | --- | --- |
| T1 | Administrator | Add a new class to an existing school and confirm it in the class list |
| T2 | Administrator | Generate the grade report of one class for an exam and export it |
| T3 | Administrator | Export reports for every class of one exam in a single file |
| T4 | Teacher | Enter grades for one class and one subject for an exam |
| T5 | Teacher | Record today's attendance for one course |
| T6 | Teacher | Find the at-risk students of your class and explain why each was flagged |
| T7 | Student | Log in with the ID number and read your latest exam result |

**SUS-10 instrument** (5-point Likert, 1 = strongly disagree … 5 = strongly agree):

1. I think that I would like to use this system frequently.
2. I found the system unnecessarily complex.
3. I thought the system was easy to use.
4. I think that I would need the support of a technical person to be able to use this system.
5. I found the various functions in this system were well integrated.
6. I thought there was too much inconsistency in this system.
7. I would imagine that most people would learn to use this system very quickly.
8. I found the system very cumbersome to use.
9. I felt very confident using the system.
10. I needed to learn a lot of things before I could get going with this system.

Scoring: odd items contribute `score − 1`, even items contribute `5 − score`; sum the ten
contributions and multiply by 2.5 → 0–100. Report mean, standard deviation and 95% CI per role.

**Recorded per task:** completion (yes/partly/no), time to completion, number of errors,
number of moderator interventions. Means and standard deviations per role go in the table in §7.1.

---

## 5. Workload reduction — before/after comparison

**Baseline (existing practice).** The participant prepares the end-of-term class report for one
class from paper/spreadsheet records: collect scores, compute per-subject averages, compute ranks,
format the report sheet.

**System condition.** The same participant produces the same artefact with
`/report` → *班级成绩报表* → *导出本班 Excel*, then *批量导出全部班级* for the whole exam.

**Measures.**

| Measure | Definition |
| --- | --- |
| Time on task (s) | stopwatch from first action to final file saved |
| Correctness | number of arithmetic/formatting errors found on review (rank order, averages, missing students) |
| Perceived effort | one-item NASA-TLX-style rating (0–10) after each condition |

**Design.** Within-subject, order counterbalanced across participants (half start with the manual
condition). Reported as mean difference with 95% CI, plus a paired comparison per participant.

**Selection criteria for a valid comparison.** School-size datasets only (≥ 20 students per class);
the same exam and class are used for both conditions.

---

## 6. Early risk identification

For one exam and one class:

1. Before seeing the dashboard, each teacher marks every student they consider at risk and writes
   the main reason.
2. The system flags 高风险 and 中风险 students for the same exam and class.
3. Compare the two sets: precision/recall of the system flags against the teacher judgement,
   and count of students flagged by the system that the teacher missed (the practically important
   category) and vice versa.
4. Teachers rate the usefulness of each supplied reason on a 3-point scale
   (not useful / somewhat useful / actionable).

This does not treat teacher judgement as ground truth; it measures whether the dashboard surfaces
the same concerns *plus* explainable ones, and whether the reasons are actionable.

---

## 7. Result templates

### 7.1 Usability (to be completed with participants)

| Role | n | Task completion | Mean SUS | SD |
| --- | --- | --- | --- | --- |
| Administrator | 3 | — | — | — |
| Teacher | 6 | — | — | — |
| Student | 15 | — | — | — |
| Overall | 24 | — | — | — |

### 7.2 Workload (to be completed with participants)

| Condition | Mean time (s) | Mean errors | Perceived effort (0–10) |
| --- | --- | --- | --- |
| Spreadsheet baseline | — | — | — |
| System | — | — | — |
| Difference | — | — | — |

### 7.3 Risk identification (to be completed with participants)

| Metric | Value |
| --- | --- |
| Precision of system flags against teacher judgement | — |
| Recall of system flags against teacher judgement | — |
| Students flagged by the system and missed by the teacher | — |
| Reason usefulness rating (mean of 3) | — |

---

## 8. Threats to validity

- **Single school, small sample.** Results describe one institution; generalising to other
  school sizes or regions needs replication.
- **Order effects.** Counterbalancing in the workload study mitigates, but does not remove,
  learning effects between conditions.
- **Demo data.** Statistical correctness is verified on synthetic data; a pilot on real
  end-of-term data is needed before institutional adoption.
- **Performance figures** are from a single machine with SQLite; a network deployment with a
  multi-user database will be slower and should be re-benchmarked.

## 9. Ethics

Participation is voluntary and anonymous, no personally identifiable information is recorded in
the evaluation dataset, and the demonstration database contains only randomly generated names and
identification numbers.
