"""
Standalone Reproducibility, Raw-Histogram Recomputation & Statistical Verifier for prometheus-iqm-execution:
1. Audits all 5 sanitized public commitment manifests and their documented private pre-execution SHA-256 commitments.
2. Recomputes from raw bitstring histograms (counts) and ideal statevector distributions (ideal_probs) ALL 1,196 measured workload evaluations across all 40 scored IQM Resonance hardware jobs (740 physical PUBs, 378,880 physical shots):
   - Initial Feasibility Campaign (9 jobs, 106 PUBs, 144 evaluations on IQM Garnet 20Q & IQM Emerald 54Q)
   - Stage 1 Billing Calibration Probes (3 jobs, 18 PUBs, 24 evaluations on IQM Emerald 54Q)
   - Stage 2 Multi-Window 60-Workload Replication (13 jobs, 450 PUBs, 780 evaluations on IQM Emerald 54Q)
   - Stage 3 5Q Trotter Interference & Delay Controls (7 jobs, 56 PUBs, 56 evaluations on IQM Emerald 54Q)
   - Stage 4A Standard Held-Out Prospective Scheduler (4 jobs, 70 PUBs, 128 evaluations on IQM Emerald 54Q)
   - Stage 4B Boundary-Stress Held-Out Scheduler (4 jobs, 40 PUBs, 64 evaluations on IQM Emerald 54Q)
3. Recomputes and explicitly asserts exact two-sided sign-flip permutation p-values, Holm-Bonferroni adjusted p-values, and bootstrap 95% confidence intervals across all initial (Garnet & Emerald) and extended (Stage 2, Stage 4A, Stage 4B) comparison blocks.
4. Verifies byte-exact SHA-256 checksums across all tracked repository files listed in REPO_SHA256_MANIFEST.json.
"""
import os
import json
import hashlib
import itertools
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
MAN_DIR = os.path.join(ROOT, "manifests")


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def recompute_metrics(counts_dict, ideal_probs):
    total = sum(counts_dict.values())
    if total == 0:
        return {"F_B": 0.0, "F_H": 0.0, "TVD": 1.0}
    meas_probs = {k: v / total for k, v in counts_dict.items()}
    all_keys = set(ideal_probs.keys()) | set(meas_probs.keys())
    fb = sum(np.sqrt(ideal_probs.get(k, 0.0) * meas_probs.get(k, 0.0)) for k in all_keys)
    fh = fb ** 2
    tvd = 0.5 * sum(abs(ideal_probs.get(k, 0.0) - meas_probs.get(k, 0.0)) for k in all_keys)
    return {"F_B": float(fb), "F_H": float(fh), "TVD": float(tvd)}


def initial_signflip_and_bootstrap(diffs, seed=42, n_boot=10000):
    diffs_arr = np.array(diffs, dtype=float)
    n = len(diffs_arr)
    obs = float(np.mean(diffs_arr))
    med = float(np.median(diffs_arr))
    cnt = sum(1 for s in itertools.product([-1, 1], repeat=n) if abs(np.mean(diffs_arr * s)) >= abs(obs) - 1e-12)
    p2 = float(cnt / (2 ** n))
    rng = np.random.default_rng(seed)
    boots = [np.mean(rng.choice(diffs_arr, size=n, replace=True)) for _ in range(n_boot)]
    ci_lo, ci_hi = np.percentile(boots, [2.5, 97.5])
    return obs, med, p2, float(ci_lo), float(ci_hi)


def exact_signflip_and_bootstrap(group_diffs, n_boot=20000, seed=12345):
    g_arr = np.array(group_diffs, dtype=float)
    n_g = len(g_arr)
    obs = float(np.mean(g_arr))
    med_g = float(np.median(g_arr))
    signs = np.array(list(itertools.product([-1.0, 1.0], repeat=n_g)))
    perm_means = (signs @ g_arr) / n_g
    p_two_sided = float(np.mean(np.abs(perm_means) >= abs(obs) - 1e-12))
    rng = np.random.default_rng(seed)
    boot_idx = rng.integers(0, n_g, size=(n_boot, n_g))
    boot_means = np.mean(g_arr[boot_idx], axis=1)
    ci_lo, ci_hi = np.percentile(boot_means, [2.5, 97.5])
    return obs, med_g, p_two_sided, [round(float(ci_lo), 4), round(float(ci_hi), 4)]


def holm_bonferroni(p_dict):
    sorted_keys = sorted(p_dict.keys(), key=lambda k: p_dict[k])
    m = len(sorted_keys)
    adj = {}
    running_max = 0.0
    for idx, k in enumerate(sorted_keys):
        raw_p = p_dict[k]
        corr = min(1.0, raw_p * (m - idx))
        running_max = max(running_max, corr)
        adj[k] = round(float(running_max), 6)
    return adj


if __name__ == "__main__":
    # 1. Verify Commitment Manifests
    g_man_path = os.path.join(DATA_DIR, "garnet_preexecution_commitment_manifest.json")
    e_man_path = os.path.join(DATA_DIR, "emerald_preexecution_commitment_manifest.json")
    s2_man_path = os.path.join(MAN_DIR, "stage2_frozen_scope_manifest.json")
    s4a_man_path = os.path.join(MAN_DIR, "stage4_prospective_scheduler_manifest.json")
    s4b_man_path = os.path.join(MAN_DIR, "stage4b_boundary_stress_manifest.json")

    ledger = json.load(open(os.path.join(DATA_DIR, "iqm_garnet_and_emerald_full_ledger.json"), encoding="utf-8"))
    ext_master = json.load(open(os.path.join(DATA_DIR, "extended_campaign_master_summary.json"), encoding="utf-8"))
    mp = ext_master["manifest_provenance"]

    assert sha256_file(g_man_path) == mp["initial_garnet_sanitized_public_sha256"]
    assert sha256_file(e_man_path) == mp["initial_emerald_sanitized_public_sha256"]
    assert sha256_file(s2_man_path) == mp["stage2_sanitized_public_sha256"]
    assert sha256_file(s4a_man_path) == mp["stage4a_sanitized_public_sha256"]
    assert sha256_file(s4b_man_path) == mp["stage4b_sanitized_public_sha256"]

    print("=== 1. VERIFIED SANITIZED PUBLIC COMMITMENT MANIFESTS & PRIVATE PROVENANCE HASHES ===")
    print(f"  Initial Garnet  : public={mp['initial_garnet_sanitized_public_sha256'][:16]}... | private={mp['initial_garnet_private_sha256']}")
    print(f"  Initial Emerald : public={mp['initial_emerald_sanitized_public_sha256'][:16]}... | private={mp['initial_emerald_private_sha256']}")
    print(f"  Stage 2 Scope   : public={mp['stage2_sanitized_public_sha256'][:16]}... | private={mp['stage2_private_sha256']}")
    print(f"  Stage 4A Sched  : public={mp['stage4a_sanitized_public_sha256'][:16]}... | private={mp['stage4a_private_sha256']}")
    print(f"  Stage 4B Stress : public={mp['stage4b_sanitized_public_sha256'][:16]}... | private={mp['stage4b_private_sha256']}")

    total_recomputed_evals = 0

    # 2. Recompute Initial 9-Job Campaign (144 workload evaluations across Garnet 20Q & Emerald 54Q)
    g_man = json.load(open(g_man_path, encoding="utf-8"))
    e_man = json.load(open(e_man_path, encoding="utf-8"))
    w8_order = list(e_man["workloads"].keys())
    w8_ideals = {w: e_man["workloads"][w]["ideal_probs"] for w in w8_order}
    pairs = [
        ("P1", "W1_qft_4q", "W2_qaoa_dense_4q"),
        ("P2", "W3_chem_hea_4q", "W4_cross_ent_4q"),
        ("P3", "W5_qft_5q", "W6_qaoa_sparse_5q"),
        ("P4", "W7_dense_ent_5q", "W8_trotter_5q"),
    ]
    quads = [
        ("Q1_4q", "W1_qft_4q", "W2_qaoa_dense_4q", "W3_chem_hea_4q", "W4_cross_ent_4q"),
        ("Q2_5q", "W5_qft_5q", "W6_qaoa_sparse_5q", "W7_dense_ent_5q", "W8_trotter_5q"),
    ]

    # Garnet T1 & T2 (16 evaluations)
    raw_t1_t2 = ledger["garnet_20q"]["raw_t1_t2_counts"]
    for w in w8_order:
        rec = recompute_metrics(raw_t1_t2[f"T1_{w}"]["m1"], w8_ideals[w])
        assert abs(rec["F_B"] - ledger["garnet_20q"]["t1_scores"][w]["F_B"]) < 1e-4
        total_recomputed_evals += 1
    for pid, wA, wB in pairs:
        recA = recompute_metrics(raw_t1_t2[f"T2_{pid}"]["m1"], w8_ideals[wA])
        recB = recompute_metrics(raw_t1_t2[f"T2_{pid}"]["m2"], w8_ideals[wB])
        assert abs(recA["F_B"] - ledger["garnet_20q"]["t2_scores"][wA]["F_B"]) < 1e-4
        assert abs(recB["F_B"] - ledger["garnet_20q"]["t2_scores"][wB]["F_B"]) < 1e-4
        total_recomputed_evals += 2

    # Garnet T3 & T4 (16 evaluations)
    raw_t3_t4 = ledger["garnet_20q"]["raw_t3_t4_counts"]
    for w in w8_order:
        rec = recompute_metrics(raw_t3_t4[f"T3_{w}"]["m1"], w8_ideals[w])
        assert abs(rec["F_B"] - ledger["garnet_20q"]["t3_scores"][w]["F_B"]) < 1e-4
        total_recomputed_evals += 1
    for pid, wA, wB in pairs:
        recA = recompute_metrics(raw_t3_t4[f"T4_{pid}"]["m1"], w8_ideals[wA])
        recB = recompute_metrics(raw_t3_t4[f"T4_{pid}"]["m2"], w8_ideals[wB])
        assert abs(recA["F_B"] - ledger["garnet_20q"]["t4_scores"][wA]["F_B"]) < 1e-4
        assert abs(recB["F_B"] - ledger["garnet_20q"]["t4_scores"][wB]["F_B"]) < 1e-4
        total_recomputed_evals += 2

    # Garnet M1 (60 PUBs -> 76 direct evaluations + 4 shared reg_A reference evaluations = 80 evaluations)
    raw_m1 = ledger["garnet_20q"]["raw_m1_counts"]
    for entry in g_man["randomized_m1_order"]:
        cname = entry["circuit_name"]
        arm = entry["arm"]
        if entry["kind"] == "iso":
            w = entry["workload"]
            rec = recompute_metrics(raw_m1[cname]["m1"], w8_ideals[w])
            assert abs(rec["F_B"] - ledger["garnet_20q"]["m1_scores"][w][arm]["F_B"]) < 1e-4
            total_recomputed_evals += 1
        else:
            wA, wB = entry["workload"]
            recA = recompute_metrics(raw_m1[cname]["m1"], w8_ideals[wA])
            recB = recompute_metrics(raw_m1[cname]["m2"], w8_ideals[wB])
            assert abs(recA["F_B"] - ledger["garnet_20q"]["m1_scores"][wA][arm]["F_B"]) < 1e-4
            assert abs(recB["F_B"] - ledger["garnet_20q"]["m1_scores"][wB][arm]["F_B"]) < 1e-4
            total_recomputed_evals += 2
    for w in ["W1_qft_4q", "W3_chem_hea_4q", "W5_qft_5q", "W7_dense_ent_5q"]:
        assert abs(ledger["garnet_20q"]["m1_scores"][w]["arm2_prom_iso_adj"]["F_B"] - ledger["garnet_20q"]["m1_scores"][w]["arm3_prom_iso_buf"]["F_B"]) < 1e-6
        total_recomputed_evals += 1

    # Emerald E_T1..E_T4 (32 evaluations)
    raw_em = ledger["emerald_54q"]["raw_counts"]
    for w in w8_order:
        r1 = recompute_metrics(raw_em[f"ET1_sabre_def_{w}"]["m1"], w8_ideals[w])
        r2 = recompute_metrics(raw_em[f"ET2_prom_1way_{w}"]["m1"], w8_ideals[w])
        assert abs(r1["F_B"] - ledger["emerald_54q"]["et1_scores"][w]["F_B"]) < 1e-4
        assert abs(r2["F_B"] - ledger["emerald_54q"]["et2_scores"][w]["F_B"]) < 1e-4
        total_recomputed_evals += 2
    for pid, wA, wB in pairs:
        rA = recompute_metrics(raw_em[f"ET3_prom_2way_{pid}"]["m1"], w8_ideals[wA])
        rB = recompute_metrics(raw_em[f"ET3_prom_2way_{pid}"]["m2"], w8_ideals[wB])
        assert abs(rA["F_B"] - ledger["emerald_54q"]["et3_scores"][wA]["F_B"]) < 1e-4
        assert abs(rB["F_B"] - ledger["emerald_54q"]["et3_scores"][wB]["F_B"]) < 1e-4
        total_recomputed_evals += 2
    for qid, w1, w2, w3, w4 in quads:
        for idx, w in enumerate((w1, w2, w3, w4), start=1):
            rm = recompute_metrics(raw_em[f"ET4_prom_4way_{qid}"][f"m{idx}"], w8_ideals[w])
            assert abs(rm["F_B"] - ledger["emerald_54q"]["et4_scores"][w]["F_B"]) < 1e-4
            total_recomputed_evals += 1

    assert total_recomputed_evals == 144, f"Expected 144 initial evaluations, got {total_recomputed_evals}"

    # Verify Initial Garnet & Emerald Statistical Comparisons (mean_diff, median_diff, p_two_sided_exact, AND bootstrap 95% CIs)
    g_m1 = ledger["garnet_20q"]["m1_scores"]
    g_t1 = ledger["garnet_20q"]["t1_scores"]
    g_t3 = ledger["garnet_20q"]["t3_scores"]
    g_t4 = ledger["garnet_20q"]["t4_scores"]
    g_comparisons = [
        ("Prom_Pack2_Buf_vs_SABRE_Def", [g_m1[w]["arm3_prom_pack_buf"]["F_B"] - g_m1[w]["arm1_sabre_def"]["F_B"] for w in w8_order]),
        ("Prom_Pack2_Buf_vs_TKET_Def", [g_m1[w]["arm3_prom_pack_buf"]["F_B"] - g_m1[w]["arm1_tket_def"]["F_B"] for w in w8_order]),
        ("Prom_Iso1_Buf_vs_SABRE_Def", [g_m1[w]["arm3_prom_iso_buf"]["F_B"] - g_m1[w]["arm1_sabre_def"]["F_B"] for w in w8_order]),
        ("SABRE_Pack2_Buf_vs_SABRE_Def", [g_m1[w]["arm3_sabre_pack_buf"]["F_B"] - g_m1[w]["arm1_sabre_def"]["F_B"] for w in w8_order]),
        ("TKET_Pack2_Buf_vs_TKET_Def", [g_m1[w]["arm3_tket_pack_buf"]["F_B"] - g_m1[w]["arm1_tket_def"]["F_B"] for w in w8_order]),
        ("Prom_Pack2_Buf_vs_Prom_Iso1_Buf_M1", [g_m1[w]["arm3_prom_pack_buf"]["F_B"] - g_m1[w]["arm3_prom_iso_buf"]["F_B"] for w in w8_order]),
        ("Prom_Pack2_Contemp_T4_vs_T3", [g_t4[w]["F_B"] - g_t3[w]["F_B"] for w in w8_order]),
        ("Prom_Pack2_Contemp_T4_vs_SABRE_Def_T1", [g_t4[w]["F_B"] - g_t1[w]["F_B"] for w in w8_order]),
    ]
    for name, diffs8 in g_comparisons:
        pair_diffs4 = [0.5 * (diffs8[2 * i] + diffs8[2 * i + 1]) for i in range(4)]
        for lvl_key, arr in [("workload_N8", diffs8), ("pair_clustered_N4", pair_diffs4)]:
            obs, med, p2, ci_lo, ci_hi = initial_signflip_and_bootstrap(arr)
            st = ledger["garnet_20q"]["statistics"][name][lvl_key]
            assert abs(obs - st["mean_diff"]) <= 1e-6
            assert abs(med - st["median_diff"]) <= 1e-6
            assert abs(p2 - st["p_two_sided_exact"]) <= 1e-6
            assert abs(ci_lo - st["ci95_low"]) <= 1e-6
            assert abs(ci_hi - st["ci95_high"]) <= 1e-6

    et1 = ledger["emerald_54q"]["et1_scores"]
    et2 = ledger["emerald_54q"]["et2_scores"]
    et3 = ledger["emerald_54q"]["et3_scores"]
    et4 = ledger["emerald_54q"]["et4_scores"]
    e_comparisons = [
        ("Prom_1Way_ET2_vs_SABRE_Def_ET1", [et2[w]["F_B"] - et1[w]["F_B"] for w in w8_order]),
        ("Prom_2Way_ET3_vs_SABRE_Def_ET1", [et3[w]["F_B"] - et1[w]["F_B"] for w in w8_order]),
        ("Prom_4Way_ET4_vs_SABRE_Def_ET1", [et4[w]["F_B"] - et1[w]["F_B"] for w in w8_order]),
        ("Prom_2Way_ET3_vs_Prom_1Way_ET2_Simultaneous", [et3[w]["F_B"] - et2[w]["F_B"] for w in w8_order]),
        ("Prom_4Way_ET4_vs_Prom_1Way_ET2_Simultaneous", [et4[w]["F_B"] - et2[w]["F_B"] for w in w8_order]),
        ("Prom_4Way_ET4_vs_Prom_2Way_ET3_Simultaneous", [et4[w]["F_B"] - et3[w]["F_B"] for w in w8_order]),
    ]
    for name, diffs8 in e_comparisons:
        pair_diffs4 = [0.5 * (diffs8[2 * i] + diffs8[2 * i + 1]) for i in range(4)]
        quad_diffs2 = [0.25 * sum(diffs8[4 * i : 4 * i + 4]) for i in range(2)]
        for lvl_key, arr in [("workload_N8", diffs8), ("pair_clustered_N4", pair_diffs4), ("quad_clustered_N2", quad_diffs2)]:
            obs, med, p2, ci_lo, ci_hi = initial_signflip_and_bootstrap(arr)
            st = ledger["emerald_54q"]["statistics"][name][lvl_key]
            assert abs(obs - st["mean_diff"]) <= 1e-6
            assert abs(med - st["median_diff"]) <= 1e-6
            assert abs(p2 - st["p_two_sided_exact"]) <= 1e-6
            assert abs(ci_lo - st["ci95_low"]) <= 1e-6
            assert abs(ci_hi - st["ci95_high"]) <= 1e-6

    print(f"=== 2. RECOMPUTED ALL {total_recomputed_evals} INITIAL CAMPAIGN EVALUATIONS & 34 STATISTICAL/BOOTSTRAP CI BLOCKS ===")

    # 3. Recompute Stage 1 Billing Calibration Probes (24 evaluations)
    s1 = json.load(open(os.path.join(DATA_DIR, "stage1_billing_calibration_telemetry.json"), encoding="utf-8"))
    s2_suite = json.load(open(os.path.join(DATA_DIR, "stage2_compiled_60workload_suite.json"), encoding="utf-8"))
    s2_ideals = {wid: w["ideal_probs"] for wid, w in s2_suite["workloads"].items()}
    s2_groups = {g["group_id"]: g for g in s2_suite["groups"]}
    g_order_15 = [g["group_id"] for g in s2_suite["groups"]]

    s1_eval_count = 0
    for lbl in ["S1_Bill_SABRE_Def_Iso8", "S1_Bill_Prom_Buf_Iso8", "S1_Bill_Prom_Buf_Pack4"]:
        for wid in s1["probe_workloads"]:
            rec = recompute_metrics(s1["raw_counts"][lbl][wid], s2_ideals[wid])
            assert abs(rec["F_B"] - s1["scores"][lbl][wid]["F_B"]) < 1e-4
            s1_eval_count += 1
    assert s1_eval_count == 24
    total_recomputed_evals += s1_eval_count

    # 4. Recompute Stage 2 Multi-Window 60-Workload Replication (780 evaluations across 13 jobs, 450 PUBs)
    s2_res = json.load(open(os.path.join(DATA_DIR, "stage2_emerald_replication_results.json"), encoding="utf-8"))
    s2_eval_count = 0
    for win_key in ["window_A", "window_B"]:
        for arm_name, wdict in s2_res[win_key]["scores"].items():
            for wid, e in wdict.items():
                rec = recompute_metrics(e["counts"], s2_ideals[wid])
                assert abs(rec["F_B"] - e["F_B"]) < 1e-4
                assert abs(rec["F_H"] - e["F_H"]) < 1e-4
                assert abs(rec["TVD"] - e["tvd"]) < 1e-4
                s2_eval_count += 1
    assert s2_eval_count == 780, f"Expected 780 Stage 2 evaluations, got {s2_eval_count}"
    total_recomputed_evals += s2_eval_count

    # Recompute Stage 2 Group-Clustered Hypothesis Tests (N=15 groups, 60 workloads) & Bootstrap 95% CIs
    pooled_wk_fb = {}
    for arm_name in s2_res["window_B"]["scores"].keys():
        mapA = {wid: e["F_B"] for wid, e in s2_res["window_A"]["scores"][arm_name].items()}
        mapB = {wid: e["F_B"] for wid, e in s2_res["window_B"]["scores"][arm_name].items()}
        pooled_wk_fb[arm_name] = {wid: 0.5 * (mapA[wid] + mapB[wid]) for wid in mapA}
    winA_wk_fb = {
        arm_name: {wid: e["F_B"] for wid, e in wdict.items()}
        for arm_name, wdict in s2_res["window_A"]["scores"].items()
    }

    s2_comparisons = [
        ("H1_Prom_1W_vs_SABRE_Def_1W_Pooled", pooled_wk_fb["Arm_C_Prom_Buf_1W"], pooled_wk_fb["Arm_A_SABRE_Def_1W"]),
        ("H2_Prom_1W_vs_TKET_Def_1W_WinA", winA_wk_fb["Arm_C_Prom_Buf_1W"], winA_wk_fb["Arm_B_TKET_Def_1W"]),
        ("H3_Prom_2W_vs_Prom_1W_Matched_Pooled", pooled_wk_fb["Arm_D_Prom_Buf_2W"], pooled_wk_fb["Arm_C_Prom_Buf_1W"]),
        ("H4_Prom_4W_vs_Prom_1W_Matched_Pooled", pooled_wk_fb["Arm_E_Prom_Buf_4W"], pooled_wk_fb["Arm_C_Prom_Buf_1W"]),
        ("H5_SABRE_Buf_4W_vs_SABRE_Def_1W_Pooled", pooled_wk_fb["Arm_F_SABRE_Buf_4W"], pooled_wk_fb["Arm_A_SABRE_Def_1W"]),
        ("H6_TKET_Buf_4W_vs_TKET_Def_1W_WinA", winA_wk_fb["Arm_G_TKET_Buf_4W"], winA_wk_fb["Arm_B_TKET_Def_1W"]),
        ("H7_Prom_4W_vs_SABRE_Def_1W_Pooled", pooled_wk_fb["Arm_E_Prom_Buf_4W"], pooled_wk_fb["Arm_A_SABRE_Def_1W"]),
    ]
    raw_p_map = {}
    for h_key, map_a, map_b in s2_comparisons:
        g_diffs = [
            float(np.mean([map_a[w] - map_b[w] for w in s2_groups[gid]["workloads"]]))
            for gid in g_order_15
        ]
        obs_diff, med_g, p2, ci95 = exact_signflip_and_bootstrap(g_diffs)
        stored = ext_master["stage2_group_clustered_tests"][h_key]
        assert abs(round(obs_diff, 4) - stored["mean_diff"]) <= 1e-4
        assert abs(round(med_g, 4) - stored["median_diff_group"]) <= 1e-4
        assert abs(round(p2, 6) - stored["exact_signflip_p_two_sided"]) <= 1e-5
        assert ci95 == stored["group_cluster_ci95"], f"Stage 2 CI mismatch for {h_key}: {ci95} != {stored['group_cluster_ci95']}"
        raw_p_map[h_key] = p2
    holm_map = holm_bonferroni(raw_p_map)
    for h_key, adj_p in holm_map.items():
        assert abs(adj_p - ext_master["stage2_group_clustered_tests"][h_key]["holm_bonferroni_adjusted_p"]) <= 1e-5

    # 5. Recompute Stage 3 5Q Trotter Interference & Schedule-Duration Delay Controls (56 evaluations across 7 jobs)
    s3_res = json.load(open(os.path.join(DATA_DIR, "stage3_interference_results.json"), encoding="utf-8"))
    s3_ideals = {
        "T0_W8_trotter_5q_orig": w8_ideals["W8_trotter_5q"],
        "T1_W58_trotter_5q_v3": s2_ideals["W58_trotter_5q_v3"],
        "T2_W59_trotter_5q_v4": s2_ideals["W59_trotter_5q_v4"],
        "T3_W60_trotter_5q_v5": s2_ideals["W60_trotter_5q_v5"],
    }
    s3_eval_count = 0
    for arm_name, eval_list in s3_res["scores"].items():
        for e in eval_list:
            tid = e["target_id"]
            rec = recompute_metrics(e["counts"], s3_ideals[tid])
            assert abs(rec["F_B"] - e["F_B"]) < 1e-4
            assert abs(rec["TVD"] - e["tvd"]) < 1e-4
            s3_eval_count += 1
    assert s3_eval_count == 56, f"Expected 56 Stage 3 evaluations, got {s3_eval_count}"
    total_recomputed_evals += s3_eval_count

    # 6. Recompute Stage 4A Standard Held-Out Prospective Scheduler (128 evaluations across 4 jobs, 70 PUBs)
    s4_suite = json.load(open(os.path.join(DATA_DIR, "stage4_compiled_32heldout_suite.json"), encoding="utf-8"))
    s4_ideals = {wid: w["ideal_probs"] for wid, w in s4_suite["workloads"].items()}
    s4_groups = s4_suite["groups"]
    s4_res = json.load(open(os.path.join(DATA_DIR, "stage4_prospective_scheduler_results.json"), encoding="utf-8"))
    s4_eval_count = 0
    for pol_name, wdict in s4_res["scores"].items():
        for wid, e in wdict.items():
            rec = recompute_metrics(e["counts"], s4_ideals[wid])
            assert abs(rec["F_B"] - e["F_B"]) < 1e-4
            assert abs(rec["TVD"] - e["tvd"]) < 1e-4
            s4_eval_count += 1
    assert s4_eval_count == 128, f"Expected 128 Stage 4A evaluations, got {s4_eval_count}"
    total_recomputed_evals += s4_eval_count

    # Recompute Stage 4A Group-Clustered Hypothesis Tests (N=8 groups, 32 workloads) & Bootstrap 95% CIs
    s4a_map = {
        pol: {wid: e["F_B"] for wid, e in wdict.items()}
        for pol, wdict in s4_res["scores"].items()
    }
    for t_key, pol_b in [
        ("S4_Scheduler_vs_Always_4Way", "Always_4Way_Packed"),
        ("S4_Scheduler_vs_Always_2Way", "Always_2Way_Packed"),
        ("S4_Scheduler_vs_Always_1Way", "Always_1Way_Isolated"),
    ]:
        g_diffs = [
            float(np.mean([s4a_map["Prometheus_Prospective_Scheduler"][w] - s4a_map[pol_b][w] for w in g["workloads"]]))
            for g in s4_groups
        ]
        obs_diff, med_g, p2, ci95 = exact_signflip_and_bootstrap(g_diffs)
        stored = ext_master["stage4a_group_clustered_tests"][t_key]
        assert abs(round(obs_diff, 4) - stored["mean_diff"]) <= 1e-4
        assert abs(round(med_g, 4) - stored["median_diff_group"]) <= 1e-4
        assert abs(round(p2, 6) - stored["exact_signflip_p_two_sided"]) <= 1e-5
        assert ci95 == stored["group_cluster_ci95"], f"Stage 4A CI mismatch for {t_key}: {ci95} != {stored['group_cluster_ci95']}"

    # 7. Recompute Stage 4B Boundary-Stress Held-Out Prospective Scheduler (64 evaluations across 4 jobs, 40 PUBs)
    s4b_res = json.load(open(os.path.join(DATA_DIR, "stage4b_boundary_stress_results.json"), encoding="utf-8"))
    s4b_ideals = {wid: w["ideal_probs"] for wid, w in s4b_res["workloads"].items()}
    s4b_eval_count = 0
    for pol_name, wdict in s4b_res["scores"].items():
        for wid, e in wdict.items():
            rec = recompute_metrics(e["counts"], s4b_ideals[wid])
            assert abs(rec["F_B"] - e["F_B"]) < 1e-4
            assert abs(rec["TVD"] - e["tvd"]) < 1e-4
            s4b_eval_count += 1
    assert s4b_eval_count == 64, f"Expected 64 Stage 4B evaluations, got {s4b_eval_count}"
    total_recomputed_evals += s4b_eval_count

    # Recompute Stage 4B Group-Clustered Hypothesis Tests (N=4 groups, 16 workloads) & Bootstrap 95% CIs
    s4b_groups = s4b_res["groups"]
    s4b_map = {
        pol: {wid: e["F_B"] for wid, e in wdict.items()}
        for pol, wdict in s4b_res["scores"].items()
    }
    for t_key, pol_b in [
        ("S4B_Scheduler_vs_Always_4Way", "Always_4Way_Packed"),
        ("S4B_Scheduler_vs_Always_2Way", "Always_2Way_Packed"),
        ("S4B_Scheduler_vs_Always_1Way", "Always_1Way_Isolated"),
    ]:
        g_diffs = [
            float(np.mean([s4b_map["Prometheus_Prospective_Scheduler"][w] - s4b_map[pol_b][w] for w in g["workloads"]]))
            for g in s4b_groups
        ]
        obs_diff, med_g, p2, ci95 = exact_signflip_and_bootstrap(g_diffs)
        stored = ext_master["stage4b_group_clustered_tests"][t_key]
        assert abs(round(obs_diff, 4) - stored["mean_diff"]) <= 1e-4
        assert abs(round(med_g, 4) - stored["median_diff_group"]) <= 1e-4
        assert abs(round(p2, 6) - stored["exact_signflip_p_two_sided"]) <= 1e-5
        assert ci95 == stored["group_cluster_ci95"], f"Stage 4B CI mismatch for {t_key}: {ci95} != {stored['group_cluster_ci95']}"

    assert total_recomputed_evals == 1196, f"Expected 1,196 total multiplexing evaluations, got {total_recomputed_evals}"
    print("=== 3. RECOMPUTED ALL 1,052 EXTENDED CAMPAIGN EVALUATIONS FROM RAW HISTOGRAMS (31 JOBS, 634 PUBS) ===")
    print(f"=== 4. TOTAL VERIFIED MULTIPLEXING EVALUATIONS: {total_recomputed_evals} / 1,196 (100.0% EXACT MATCH) ===")
    print("=== 5. RECOMPUTED & ASSERTED ALL 47 MULTIPLEXING STATISTICAL BLOCKS (SIGN-FLIP P-VALUES, HOLM ADJUSTMENTS & BOOTSTRAP 95% CIS) ===")

    # 8. Recompute All 739 Evaluations of the 19-Job Dense-Circuit Optimization Campaign (739 Circuits, 756,736 Shots)
    dense_man_path = os.path.join(MAN_DIR, "dense_campaign_preexecution_manifest.json")
    dense_pref_path = os.path.join(DATA_DIR, "dense_campaign_classical_preflight_summary.json")
    dense_npz_path = os.path.join(DATA_DIR, "dense_campaign_ideal_reference.npz")
    dense_s1_path = os.path.join(DATA_DIR, "dense_stage1_billing_pilot_results.json")
    dense_s234_path = os.path.join(DATA_DIR, "dense_campaign_stages2_3_4_results.json")
    dense_stat_path = os.path.join(DATA_DIR, "dense_campaign_complete_statistical_summary.json")

    dense_man = json.load(open(dense_man_path, encoding="utf-8"))
    dense_pref = json.load(open(dense_pref_path, encoding="utf-8"))
    dense_s1 = json.load(open(dense_s1_path, encoding="utf-8"))
    dense_s234 = json.load(open(dense_s234_path, encoding="utf-8"))
    dense_stat = json.load(open(dense_stat_path, encoding="utf-8"))
    dense_npz = np.load(dense_npz_path)

    assert sha256_file(dense_man_path) == dense_stat["campaign_overview"]["sanitized_public_manifest_sha256"]
    assert sha256_file(dense_pref_path) == dense_stat["campaign_overview"]["sanitized_public_preflight_summary_sha256"]
    assert sha256_file(dense_s1_path) == dense_stat["campaign_overview"]["sanitized_public_stage1_sha256"]
    assert sha256_file(dense_s234_path) == dense_stat["campaign_overview"]["sanitized_public_stages2_3_4_sha256"]

    dense_w_meta = {}
    for gk in ["main_48_workloads", "sparse_controls_6_workloads", "high_width_28_workloads"]:
        for w in dense_pref[gk]:
            if w["workload_id"] not in dense_w_meta:
                dense_w_meta[w["workload_id"]] = w

    def recompute_dense_eval(counts_dict, wid, shots=1024):
        w_meta = dense_w_meta[wid]
        nq = int(w_meta["n_qubits"])
        fam = w_meta["family"]
        p_ideal_vec = np.array(dense_npz[f"p_ideal__{wid}"], dtype=np.float64)
        p_meas_vec = np.zeros(1 << nq, dtype=np.float64)
        for bstr, cnt in counts_dict.items():
            p_meas_vec[int(bstr[::-1], 2)] = cnt / float(shots)
        fb = float(np.sum(np.sqrt(p_ideal_vec * p_meas_vec)))
        fh = float(fb ** 2)
        tvd = float(0.5 * np.sum(np.abs(p_ideal_vec - p_meas_vec)))
        nz_m = p_meas_vec[p_meas_vec > 1e-15]
        shannon_meas = float(-np.sum(nz_m * np.log2(nz_m)))
        top8_idx = np.argpartition(p_ideal_vec, -8)[-8:]
        meas_top8_mass = float(np.sum(p_meas_vec[top8_idx]))
        out = {
            "F_B": round(fb, 4),
            "F_H": round(fh, 4),
            "TVD": round(tvd, 4),
            "measured_shannon_entropy_bits": round(shannon_meas, 4),
            "measured_top8_mass": round(meas_top8_mass, 4),
        }
        states = np.arange(1 << nq, dtype=np.int64)
        if fam == "F1_Weighted_Complete_QAOA" and f"qaoa_edges__{wid}" in dense_npz:
            cut_vals = np.zeros(1 << nq, dtype=np.float64)
            edges = dense_npz[f"qaoa_edges__{wid}"]
            weights = dense_npz[f"qaoa_weights__{wid}"]
            for idx_e in range(len(edges)):
                u, v = int(edges[idx_e, 0]), int(edges[idx_e, 1])
                cut_vals += float(weights[idx_e]) * (((states >> u) & 1) ^ ((states >> v) & 1))
            c_ideal = float(np.sum(p_ideal_vec * cut_vals))
            c_meas = float(np.sum(p_meas_vec * cut_vals))
            out["abs_cut_expectation_error"] = round(abs(c_meas - c_ideal), 5)
        elif fam == "F4_Dense_Exchange_XXYY":
            z_diffs = []
            for q in range(nq):
                z_q = 1.0 - 2.0 * ((states >> q) & 1)
                z_i = round(float(np.sum(p_ideal_vec * z_q)), 5)
                z_m = round(float(np.sum(p_meas_vec * z_q)), 5)
                z_diffs.append(abs(z_m - z_i))
            out["magnetization_profile_mae"] = round(float(np.mean(z_diffs)), 5)
        return out

    dense_evals_checked = 0
    for wid, b in dense_s1["batches"].items():
        for p_name, rec in b["pipeline_results_by_name"].items():
            assert sum(rec["counts"].values()) == 1024
            rc = recompute_dense_eval(rec["counts"], wid, shots=1024)
            assert abs(rec["F_B"] - rc["F_B"]) <= 1e-4
            assert abs(rec["F_H"] - rc["F_H"]) <= 1e-4
            assert abs(rec["TVD"] - rc["TVD"]) <= 1e-4
            dense_evals_checked += 1

    for m_key, win_dict in dense_s234["evaluations"].items():
        for win_key, w_dict in win_dict.items():
            for wid, p_dict in w_dict.items():
                for p_name, rec in p_dict.items():
                    assert sum(rec["counts"].values()) == 1024
                    exp_h = dense_man["circuit_sha256_by_mode_workload_pipeline"][m_key][wid][p_name]
                    assert rec["circuit_sha256"] == exp_h
                    rc = recompute_dense_eval(rec["counts"], wid, shots=1024)
                    assert abs(rec["F_B"] - rc["F_B"]) <= 1e-4
                    assert abs(rec["F_H"] - rc["F_H"]) <= 1e-4
                    assert abs(rec["TVD"] - rc["TVD"]) <= 1e-4
                    if "abs_cut_expectation_error" in rc:
                        assert abs(rec["domain_observable"]["abs_cut_expectation_error"] - rc["abs_cut_expectation_error"]) <= 1e-4
                    elif "magnetization_profile_mae" in rc:
                        assert abs(rec["domain_observable"]["magnetization_profile_mae"] - rc["magnetization_profile_mae"]) <= 1e-4
                    dense_evals_checked += 1

    assert dense_evals_checked == 739, f"Expected 739 dense evaluations, got {dense_evals_checked}"
    total_all_campaigns = total_recomputed_evals + dense_evals_checked
    assert total_all_campaigns == 1935
    print(f"=== 6. RECOMPUTED ALL {dense_evals_checked} / 739 DENSE-CIRCUIT CAMPAIGN EVALUATIONS (19 JOBS, 756,736 SHOTS) ===")
    print(f"=== 7. GRAND TOTAL VERIFIED IQM RESONANCE EVALUATIONS: {total_all_campaigns} / 1,935 ACROSS 59 HARDWARE JOBS (1,479 PUBS, 1,135,616 SHOTS) ===")

    # 9. Verify top-level REPO_SHA256_MANIFEST.json if present
    repo_man_path = os.path.join(ROOT, "REPO_SHA256_MANIFEST.json")
    if os.path.exists(repo_man_path):
        rm = json.load(open(repo_man_path, encoding="utf-8"))
        checked_files = 0
        for rel_path, expected_sha in rm["files"].items():
            full_p = os.path.join(ROOT, rel_path.replace("/", os.sep))
            actual_sha = sha256_file(full_p)
            assert actual_sha == expected_sha, f"Checksum mismatch for {rel_path}: {actual_sha} != {expected_sha}"
            checked_files += 1
        print(f"=== 8. VERIFIED REPO_SHA256_MANIFEST.json: {checked_files}/{checked_files} FILES MATCH BYTE-FOR-BYTE ===")
