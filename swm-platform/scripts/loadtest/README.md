# GPS Ingestion Load Test Suite

This suite benchmarks the ingestion endpoint for:

- 600 simulated trucks
- 3000 events/sec sustained traffic
- burst traffic behavior
- latency benchmark
- failure benchmark
- JSON + Markdown report generation

## Scenarios

1. steady_traffic
- Fixed rate at target EPS.

2. burst_traffic
- 20-second cycle: 12 seconds baseline (~55% target) + 8 seconds burst (~180% target).

3. latency_benchmark
- Lower rate benchmark (~40% target) focused on latency profile.

4. failure_benchmark
- Injects invalid payloads (20%) to benchmark failure-path behavior.

## Usage

From repository root:

```bash
uv run python scripts/loadtest/gps_ingestion_load_test.py \
  --base-url http://127.0.0.1:8001 \
  --endpoint /webhook/gps \
  --trucks 600 \
  --target-eps 3000 \
  --duration-seconds 30 \
  --concurrency 1200
```

Or use the Makefile target:

```bash
make loadtest-gps
```

Override defaults when needed:

```bash
make loadtest-gps LOADTEST_EPS=3500 LOADTEST_DURATION=45 LOADTEST_CONCURRENCY=1600
```

## Outputs

Reports are generated in `scripts/loadtest/reports`:

- `gps-loadtest-<timestamp>.json`
- `gps-loadtest-<timestamp>.md`

## Notes

- The suite uses the `X-Vendor-Id` header and evenly distributes devices across vendor_a/vendor_b/vendor_c for vendor breakdown reporting.
- Payloads are sent to `POST /webhook/gps` as array payloads.
- Failure scenario includes malformed payload types to exercise validation and quarantine paths.
