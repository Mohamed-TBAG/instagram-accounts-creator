# ReDroid Stability and Identity Consistency Plan

## Scope
Build a stable ReDroid boot pipeline with measurable identity consistency, without relying on unsupported assumptions about containerized kernel and CPU virtualization.

## Constraints to Accept Up Front
1. ReDroid in Docker shares host kernel.
2. Host CPU traits can appear in Android-facing low-level files.
3. `ro.product.*` customization does not fully emulate physical SoC/hardware signatures.
4. Boot stability is higher priority than aggressive property overrides.

## Goal
Deliver a repeatable flow where:
1. Container boots reliably.
2. Supported identity fields are coherent and auditable.
3. Unsupported surfaces are explicitly documented and monitored.

## Phase 1: Fingerprint Surface Inventory
1. Add a boot-time audit dump command set and save output per iteration.
2. Capture at minimum:
3. `getprop`
4. `adb shell settings get secure android_id`
5. `adb shell cat /proc/version`
6. `adb shell cat /proc/cpuinfo`
7. `adb shell cat /sys/class/net/eth0/address`
8. Persist to `logs/fingerprint_audit/<timestamp>_<container>.txt`.

### Acceptance Criteria
1. Every successful boot produces one audit file.
2. Audit file includes both mutable and immutable surfaces.

## Phase 2: Property Mount Isolation Matrix
1. Run controlled startup matrix:
2. Baseline: no prop mounts.
3. System-only mount.
4. Vendor-only mount.
5. Product-only mount.
6. System+Vendor.
7. System+Product.
8. Vendor+Product.
9. All mounts.
10. For each mode, record:
11. Boot success/failure.
12. Time to `sys.boot_completed=1`.
13. First failure reason and tail logs.

### Acceptance Criteria
1. Produce one matrix table with pass/fail and boot duration.
2. Identify minimal stable mount combination.

## Phase 3: Coherent Profile Validation Gate
1. Build strict profile schemas in config for each device profile.
2. Validate before container start:
3. Brand/model/name/device consistency.
4. Fingerprint string coherence.
5. Security patch date format.
6. Incremental/build id format.
7. Abort startup on invalid profile values.

### Acceptance Criteria
1. Invalid profile fails before docker run.
2. Valid profile proceeds consistently across runs.

## Phase 4: Runtime Identity Application Policy
1. Split identity operations into:
2. Pre-boot properties via safe mounts.
3. Post-boot settings writes for stable keys only.
4. Keep runtime writes limited to:
5. `android_id`
6. `device_name`
7. `bluetooth_name`
8. Stop forcing fields proven unstable or non-persistent in ReDroid.

### Acceptance Criteria
1. Runtime identity apply never causes boot failure.
2. Post-boot verification reports only supported fields as strict checks.

## Phase 5: Verification and Reporting
1. Add one verification summary per iteration:
2. `boot_mode`
3. `boot_time_seconds`
4. `adb_ready`
5. strict check results
6. non-strict observed values
7. Save as structured JSON under `logs/identity_reports/`.

### Acceptance Criteria
1. Each iteration has a machine-readable report.
2. Failures include actionable reason and logs tail.

## Phase 6: Safe Rollout
1. Start with baseline mode in production loop.
2. Enable mount mode only after matrix confirms stability.
3. Add feature flags in `.env`:
4. `REDROID_USE_PROP_MOUNTS`
5. `REDROID_PROP_MOUNT_MODE` (`none|system|vendor|product|combo|all`)
6. `REDROID_AUDIT_ENABLED`
7. `REDROID_VERIFY_STRICT`

### Acceptance Criteria
1. Rollout can be toggled without code edits.
2. Regressions can be isolated by feature flags.

## Deliverables
1. Fingerprint audit exporter.
2. Prop mount matrix runner.
3. Profile validation gate.
4. Structured verification report output.
5. `.env` flag documentation.
6. One final runbook with known limits and supported identity surfaces.

## Definition of Done
1. Baseline boot reliability is stable across 20 consecutive runs.
2. Selected mount mode passes 20 consecutive runs.
3. Audit and identity reports are generated for every run.
4. Failure reasons are deterministic and reproducible from logs.
