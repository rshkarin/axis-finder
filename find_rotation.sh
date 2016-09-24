#!/bin/bash
current_dir=$1
start_idx=$2
step=$3
end_idx=$4

for AXIS in {950..1050..5}; do \
  tofu tomo --absorptivity --darks ${current_dir}/dark/ --flats ${current_dir}/flat/ \
            --projections ${current_dir}/proj360/ --angle 0.00314159265 \
            --axis ${AXIS} --method fbp \
            --output ${current_dir}/slices_axis/slice-${AXIS}-%05i.tif \
            --y 1100 --height 1 --number 2000 \
; done
