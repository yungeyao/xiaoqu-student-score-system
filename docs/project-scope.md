# Project Scope — Design and Development of a Web-Based Student Management System

This document fixes the research framing of the project and maps each objective to concrete
implementation and to the evidence that already exists in the repository.

---

## 1. Title

**Design and Development of a Web-Based Student Management System with Role-Based Access Control and Academic Performance Analytics**

## 2. Short description

> This project focuses on developing a web-based student management system that consolidates
> student records, course enrolment, attendance and grades into a single platform for
> administrators, teachers and students. By integrating a relational database with role-based
> access control and automated report generation, the system aims to replace fragmented
> spreadsheet-based workflows with accurate, secure and real-time academic data. The project also
> provides a performance dashboard that helps teachers identify at-risk students early. Ultimately,
> it seeks to reduce administrative workload, minimise data-entry errors and improve the quality
> of academic decision-making.

## 3. Research objectives

1. To design and develop a web-based student management system that supports student registration,
   course enrolment, attendance tracking and grade management for multiple user roles.
2. To integrate a relational database with role-based access control and automated reporting
   services, ensuring data accuracy, security and real-time accessibility.
3. To evaluate the system's usability, performance and effectiveness in reducing administrative
   workload through user testing with administrators, teachers and students.

## 4. Scope

### In scope

| Capability | Implemented as |
| --- | --- |
| Student registration / records | `student`, `banji`, `school`, `xueqi`, `subject`, `teacher`, `category` tables; pages `/student`, `/banji`, `/teacher`, `/school`, `/xueqi`, `/subject` |
| Course enrolment | `course` and `enrollment` tables; pages `/course`, `/enrollment`, bulk enrolment at `/enrollment/batch` |
| Attendance tracking | `attendance` table; `/attendance` (whole-class entry per course + date, per-day and per-student attendance rate) |
| Grade management | `kaoshi`, `kaoshi_set`, `kaohao`, `chengji` tables; `/luru` (matrix entry, Excel import/export), `/chengji` (query), `/kaohao` (exam numbers + printable slips) |
| Role-based access control | `auth_rule` / `auth_group` / `auth_group_access` + `services/permission.py` (menu rules, URL rules, data-scope whitelist) |
| Automated report generation | `routers/report.py` — printable class report, single-class workbook, whole-exam batch workbook (`/report`, `/api/report/banji.xlsx`, `/api/report/all.xlsx`) |
| Academic performance analytics | `services/stats.py` + `services/tongji.py` (class / grade / school-level statistics), `/tongji/bj|nj|sch`, charts |
| At-risk student dashboard | `services/risk.py` + `/risk` (explainable rule-based risk score, four levels, reasons, Excel export) |
| Student self-service view | `/student` portal: own scores and trend chart (`routers/portal.py`) |

### Out of scope

Timetabling, fee/billing, library, transport, staff payroll, mobile applications and any
third-party messaging integration. Authentication is session-cookie based rather than OAuth/SSO.

## 5. Objective → implementation → evidence

### Objective 1 — multi-role platform for registration, enrolment, attendance and grades

| Requirement | Implementation | Evidence |
| --- | --- | --- |
| Student registration & records | `app/models/people.py`, `app/registry.py`, `routers/generic.py` | `/student` page renders 480 students (`seed/check_pages.py`) |
| Course enrolment | `app/models/teaching.py::Course/Enrollment`, `routers/api_teaching.py` | `seed/check_teaching.py` items 2–3: 120 courses, 2400 enrolments, batch add/remove round-trip |
| Attendance tracking | `Attendance` model + `/attendance` + `/api/attendance/*` | `check_teaching.py` items 4–6: 20-student class load, save, idempotent re-save, per-student rate |
| Grade management | `models/kaoshi.py`, `models/chengji.py`, `services/chengji_io.py`, `routers/api_chengji.py` | `seed/check_io.py`: exam-number idempotency + Excel round-trip; `check.py` items 3–5 |
| Multiple user roles | `Admin` / `Student` login entities, 职务-based roles, RBAC tables | `check_teaching.py` item 21–24: teacher sees 240 of 480 students, cross-class access rejected, student blocked from admin pages |

### Objective 2 — relational database, RBAC and automated reporting

| Requirement | Implementation | Evidence |
| --- | --- | --- |
| Relational database | 26 tables, foreign-key style integer relations, soft delete, integer timestamps (`app/models/`) | `seed/bench.py` prints row counts; DB ≈ 1.6 MB for 480 students / 7200 grades / 9600 attendance rows |
| Data accuracy | Single source of statistical formulas (`services/stats.py`), statistics recomputed from the grades table | `check.py` section 2: SQL cross-validation of class/grade/school averages, 0 mismatches |
| Role-based access control | rule + role + data-scope whitelist | `check.py` section 6 and `check_teaching.py` section 6 |
| Automated reporting | `routers/report.py` (printable + 2 workbook builders) | `check_teaching.py` section 5: printable report, single-class xlsx, 24-class batch workbook (25 sheets) |
| Real-time accessibility | server-rendered pages + JSON APIs; statistics refreshed on demand | `bench.py` P95 figures below 70 ms for read paths |

### Objective 3 — evaluation of usability, performance and workload reduction

| Measure | Instrument | Status |
| --- | --- | --- |
| Performance | `seed/bench.py` (9 endpoints, P50/P95/max) | **Executed** — see [`evaluation.md`](evaluation.md) §3 |
| Functional correctness | `seed/check*.py` (5 scripts, 102 assertions) | **Executed** — all passing |
| Usability | SUS-10 questionnaire + task completion script | Protocol ready in `evaluation.md` §4; requires participant sessions |
| Workload reduction | Before/after time-on-task protocol for report preparation | Protocol ready in `evaluation.md` §5; requires participant sessions |
| Early risk identification | Agreement between system flags and teacher judgement | Protocol ready in `evaluation.md` §6; requires participant sessions |

## 6. Roles and permissions

| Role | Determined by | Data scope |
| --- | --- | --- |
| Super administrator | `Auth.administrator` (ids 1, 2) | everything |
| Principal / vice-principal / teaching director | 职务 `10701` / `10703` / `10705` | all classes of own school |
| Class teacher (班主任) | current record in `ban_zhu_ren` | own class |
| Subject teacher | current-semester `fen_gong` | classes taught |
| Student | `student` table login | own grades only |

## 7. Stack and deployment

- Python 3.10+ (verified on 3.12 and 3.13), FastAPI, SQLAlchemy 2.0, Jinja2, Uvicorn.
- SQLite by default (`data/cj.db`); the database URL is a single constant in `app/core/config.py`,
  so MySQL/PostgreSQL only requires changing that value plus the driver.
- Front end: X-admin 2.2 shell, layui components, Apache ECharts charts (see README for licences).
- Single process, no external services; `python run.py` serves on `127.0.0.1:8000`.

## 8. Deliverables

1. Working web application (this repository).
2. Seeded demonstration database (`python -m seed.seed --reset`).
3. Five automated verification scripts and one performance benchmark.
4. Project documentation: `README.md`, this scope document, `docs/evaluation.md`.
5. Screenshots of the main workflows in `docs/screenshots/`.
