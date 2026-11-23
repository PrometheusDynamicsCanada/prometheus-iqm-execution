# Parallel Execution & Dense Compilation on IQM Hardware

*Portfolio Hub: [Prometheus Quantum Overview](https://github.com/PrometheusDynamicsCanada/prometheus-quantum-overview) · [Detailed Technical Report](DETAILED_TECHNICAL_REPORT.md) · [Public Disclosure](PUBLIC_DISCLOSURE.md)*

## Introduction

- **The question:** On square-lattice IQM quantum processors, how much can simultaneous multi-circuit execution increase throughput per credit on small jobs, and how much can compilation improve wider non-local circuits?
- **The test:** Across `59` live IQM Resonance jobs (`1,479` PUBs, `1,935` workload evaluations, `1,135,616` physical shots on `54Q` `IQM Emerald` and `20Q` `IQM Garnet`), we ran two separate studies against Qiskit SABRE and Quantinuum TKET: Study 1 (`40` jobs) tested `4-way` simultaneous execution of `4Q-5Q` circuits, and Study 2 (`19` jobs) tested `7Q-17Q` non-local compilation (including equal-budget `8`-seed controls and identical initial qubit subgraphs).
- **The finding:** In Study 1, `4-way` simultaneous execution retained **`120/120` passing circuits (`F_B >= 0.90`)** and delivered **`3.00x` qualifying workloads per IQM credit** (`7.50` vs. `22.50` credits). In Study 2, Prometheus improved output-distribution agreement by **`+3.73%` (`39/48` wins)** vs. equal-budget `SABRE K=8` and **`+7.57%` (`46/48` wins)** vs. `TKET K=8` at `7Q-12Q`, and **`+9.37%` (`12/12` wins)** vs. SABRE at `13Q-17Q`.
- **The significance:** Lowers IQM credit consumption by up to `3x` on small circuits while reducing routing depth up to `60.6%` on wider square-lattice circuits.
- **The boundary:** On simple 1D chains requiring `0` routing SWAPs, Prometheus and SABRE performed equivalently (`p = 0.4375`), and blind `4-way` packing degraded `5Q` Trotter rings unless stepped down by the scheduler (`99.0%` loss recovery).
- **The evidence:** Opening scheduler chart and summary table below, with full Stage 2-4 tables, scientific figures, and raw-histogram verification underneath.

![IQM Buffered 4-Way Parallel Execution and Scheduler Controls](assets/fig2_iqm_stage3_interference_and_stage4_scheduler.png)
*Opening summary: `4-way` simultaneous execution on 54Q IQM Emerald (`3.00x` qualifying/credit) and held-out prospective scheduler recovery (`99.0%`).*

---

## Executive Summary (`54Q` `IQM Emerald` Headline Stages, `59` Total Jobs, `1,135,616` Shots)

*Hardware IDs:* Parallel `01a19ff2..`..`01a1a47b..` (`40` jobs); Dense `01a1a579..`..`01a1a5a8..` (`19` jobs).

| Study & Experimental Arm | Scope (`Evals`) | Output Agreement $F_B$ `*(mean / med)*` `(↑)` | Squared Hellinger $F_H$ `*(mean)*` `(↑)` | `TVD` `*(mean)*` `(↓)` | `CZ` Gates / Depth `*(mean)*` `(↓)` | Credits / Yield Outcome |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Study 1 (`4Q-5Q`): SABRE `1-Way`** | `120` (`120` PUBs) | `0.9662` / `0.9757` | `0.9343` | `0.1770` | `21.45` / `55.72` | `22.50 cr` (`116/120` pass, `1.00x`) |
| **Study 1 (`4Q-5Q`): Prom `1-Way`** | `120` (`120` PUBs) | **`0.9754` / `0.9805`** | **`0.9518`** | **`0.1502`** | **`20.48` / `49.62`** | `22.50 cr` (**`120/120` pass**, `p = 0.00092`) |
| **Study 1 (`4Q-5Q`): Prom `4-Way` Packed** | `120` (**`30` PUBs**) | `0.9705` / `0.9778` | `0.9423` | `0.1632` | **`20.48` / `49.62`** | **`7.50 cr` (`120/120`, `3.00x` / credit)** |
| **Study 2 (`7Q-12Q` Dense): TKET `K=8`** | `96` (`48` wklds) | `0.6869` / `0.7275` | `0.5035` | `0.5453` | `251.04` / `127.42` | `2 / 48` vs. Prom |
| **Study 2 (`7Q-12Q` Dense): SABRE `K=8`** | `96` (`48` wklds) | `0.7123` / `0.7441` | `0.5385` | `0.5126` | `152.08` / `81.58` | `9 / 48` vs. Prom |
| **Study 2 (`7Q-12Q` Dense): Prom `K=8`** | `96` (`48` wklds) | **`0.7389` / `0.7919`** | **`0.5766`** | **`0.4766`** | **`139.42` / `54.42`** | **`+3.73%` vs. S (`39/48`) · `+7.57%` vs. T (`46/48`)** |
| **Study 2 (`13Q-17Q` Dense): Prom `K=8`** | `18` (`12` wklds) | **`0.2022` / `0.1963`** | **`0.0503`** | **`0.9285`** | **`364.17` / `71.67`** | **`+9.37%` vs. SABRE (`12/12` wins, `-60.6%` depth)** |

*Metric Key:* Output-distribution agreement is Classical Bhattacharyya Overlap $F_B = \sum_x \sqrt{P_{\text{ideal}}(x)P_{\text{meas}}(x)}$ (Studio `"State Fidelity"`); $F_H = F_B^2$.

---

## Inspect the Evidence & Reproduce Supported Checks Offline

- **Command:** `python scripts/verify_iqm_resonance_ledger.py`
- **Dependencies & measured runtime:** Python 3 + `numpy` + `scipy` (`0` cloud credentials, **`~3.25 s`** measured runtime; recomputes all `1,935` evaluations, `47` bootstrap/sign-flip statistical blocks, and SHA-256 digests).
- **Start a pilot:** [william@prometheusdynamics.ca](mailto:william@prometheusdynamics.ca) | [prometheusdynamics.ca](https://prometheusdynamics.ca)

---

## Full Stage-by-Stage Controls & Scientific Figures

<details>
<summary><strong>1. Complete Dense Compilation Stages 2-4 & Spatial Multiplexing Controls - Click to expand</strong></summary>

- **Default `K=1` Baselines (`7Q-12Q`, `48` workloads):** `P1_SABRE_O3_Fixed` $F_B = 0.6982 / 0.7178$ (`+5.83%` Prom lead, `43W/4L/1T`); `P2_TKET_Standard` $F_B = 0.6780 / 0.7058$ (`+8.98%` Prom lead, **`48/48` wins**); `P4_TKET_Preproc_SABRE_K8` $F_B = 0.7121 / 0.7673$ (`+3.76%` Prom lead, `39/48` wins).
- **Stage 3 Identical Initial Subgraph (`16` workloads, `01a1a5a1, 01a1a5a2, 01a1a5a8`):** Prom **`0.7222 / 0.7341`** vs. `SABRE K=8` `0.6852 / 0.6883` (**`+5.40%`, `16/16` wins**) & `TKET K=8` `0.6712 / 0.6865` (**`+7.60%`, `16/16` wins**).
- **Stage 3 Sparse 1D Chain Control (`6` workloads, `0` SWAPs):** `SABRE K=8` `0.8982` vs. Prom `0.8877` (`-1.16%`, `p = 0.4375`).
- **Stage 4A/4B Held-Out Scheduler:** `32`-workload Stage 4A `Prom Scheduler` `0.9785` (`1.80x/cr`, min `F_B = 0.9501`); `16`-workload Stage 4B Stress `Prom Scheduler` **`0.9458` (`99.0%` loss recovery vs. `0.9078` blind `4-way`)**.

</details>

<details>
<summary><strong>2. Additional Multi-Panel Dense & Parallel Figures - Click to expand</strong></summary>

![Figure 1A: Dense-Circuit Stage 2 Hardware Overlap and Families](assets/fig1_dense_stage2_parity_and_families.png)

![Figure 2A: Dense-Circuit Stage 3 Matched-Placement and Stage 4 High-Width](assets/fig2_dense_stage3_stage4_and_exec_manager.png)

![Figure 1B: Spatial Multiplexing Stage 2 Multi-Window Replication](assets/fig1_iqm_stage2_multiwindow_replication.png)

</details>
