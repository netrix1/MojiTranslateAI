#!/usr/bin/env bash
set -euo pipefail
BASE="http://localhost:8000"
JOB=$(curl -s -X POST "$BASE/jobs" | python3 -c "import sys, json; print(json.load(sys.stdin)['job_id'])")
echo "job_id=$JOB"
echo "Upload a page:"
echo "curl -X POST $BASE/jobs/$JOB/pages/1/image -F file=@/path/to/page.jpg"
echo "Run pipeline:"
echo "curl -X POST $BASE/pipeline/run/$JOB/page/1"
