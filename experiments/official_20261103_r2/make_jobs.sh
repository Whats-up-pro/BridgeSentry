#!/usr/bin/env bash
# make_jobs.sh <bench>... -> jobs on stdout: bench variant seeds seed budget
for b in "$@"; do for v in vulnerable patched; do for s in llm random; do
  for seed in 1042 2042 3042 4042 5042; do echo "$b $v $s $seed 20"; done; done; done; done
