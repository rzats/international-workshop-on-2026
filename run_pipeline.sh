#!/bin/bash
set -e
rm -rf data/aligned data/features data/reliability data/results
python3 src/align.py > data/pipeline_align.log 2>&1
python3 src/reliability.py > data/pipeline_rel.log 2>&1
for k in carol alice pride frankenstein holmes leaves timemachine treasure jungle dracula walden tomsawyer baskerville moby; do
  python3 src/experiment.py $k
done > data/pipeline_exp.log 2>&1
python3 src/aggregate.py > data/pipeline_agg.log 2>&1
python3 src/figures.py > data/pipeline_fig.log 2>&1
echo PIPELINE_DONE
