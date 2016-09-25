import os
import sys
import argparse
import importlib
import ast
import logging
import subprocess
import numpy as np
from skimage import io

def get_sample_paths(search_dir, sample_names, tomo_folder='tomo'):
    out = []

    for root, dirs, files in os.walk(search_dir):
        for sample_name in sample_names:
            if tomo_folder in os.path.basename(root) and \
               sample_name in root:
                out.append(root)

    return out

def run_tofu(sample_paths, proj_folder='proj360', num_axes=40):
    for path in sample_paths:
        sample_name = os.path.basename(os.path.split(path)[0])
        proj_path = os.path.join(path, proj_folder)
        projs = [f for f in os.listdir(proj_path) \
                 if os.path.isfile(os.path.join(proj_path, f))]

        data = io.imread(os.path.join(proj_path, projs[0]))
        height, width = data.shape
        hc,wc = int(height/2), int(width/2)

        rot_axes = range(wc-num_axes, wc+num_axes+1)
        y_pos = hc
        reco_height = 1
        num_proj = len(projs) - 1
        args_fmt = {'projFolder': proj_folder, \
                    'angleRad': 2 * np.pi / float(num_proj), \
                    'yPos': y_pos, \
                    'recoHeight': reco_height, \
                    'projNum': num_proj}

        for rot_axis in rot_axes:
            args_fmt['axisPos'] = rot_axis

            cmd_template = 'tofu tomo ' \
            '--absorptivity ' \
            '--darks dark/ ' \
            '--flats flat/ ' \
            '--projections {projFolder}/ ' \
            '--angle {angleRad} ' \
            '--axis {axisPos} ' \
            '--method fbp ' \
            '--output slices_axis/slice-{axisPos}-%05i.tif ' \
            '--y {yPos} ' \
            '--height {recoHeight} ' \
            '--number {projNum}'

            app = cmd_template.format(**args_fmt)
            process = subprocess.Popen(app, shell=True, cwd=path)
            streamdata = process.communicate()[0]
            rc = process.returncode

            print '{0} [Axis: {1}]'.format(sample_name, rot_axis)

def start_reconstruction(search_dir, sample_names, num_axes):
    sample_paths = get_sample_paths(search_dir, sample_names)
    run_tofu(sample_paths, num_axes=num_axes)

#http://stackoverflow.com/questions/2859674/converting-python-list-of-strings-to-their-type
def _tryeval(val):
    try:
        val = ast.literal_eval(val)
    except ValueError:
        pass
    return val

def _list_type(string):
    lst = string.replace('[','')
    lst = lst.replace(']','')
    lst = lst.split(',')
    lst = [k.replace("'", "").replace('"', '').replace(" ", "") for k in lst]
    lst = [_tryeval(l) for l in lst]
    return lst

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("-i", "--search_dir", \
                        help="Path to the folder containing the splitted data of samples", \
                        type=str, \
                        required=True)
    parser.add_argument("-n", "--sample_names", \
                        help="List of sample names to process", \
                        type=_list_type, \
                        required=True)
    parser.add_argument("-a", "--num_axes", \
                        help="The number of axes to calculate", \
                        type=int, \
                        default=40)

    args = parser.parse_args()

    start_reconstruction(args.search_dir, \
                         args.sample_names, \
                         args.num_axes)

if __name__ == "__main__":
    sys.exit(main())
