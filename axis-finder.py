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

def run_tofu(sample_paths, \
             proj_folder='proj360', \
             num_axes=40, \
             tomo=True, \
             slices_per_device=None, \
             overall_angle=None, \
             roll_angle=None, \
             lamino_angle=None, \
             z_param=None, \
             param_region=None, \
             y_pos=None, \
             reco_height=1):
    for path in sample_paths:
        sample_name = os.path.basename(os.path.split(path)[0])
        proj_path = os.path.join(path, proj_folder)
        projs = [f for f in os.listdir(proj_path) \
                 if os.path.isfile(os.path.join(proj_path, f))]

        data = io.imread(os.path.join(proj_path, projs[0]))
        height, width = data.shape
        hc,wc = int(height/2), int(width/2)

        rot_axes = range(wc-num_axes, wc+num_axes+1)

        if y_pos is None:
            y_pos = hc

        num_proj = len(projs) - 1
        args_fmt = {'projFolder': proj_folder, \
                    'angleRad': 2 * np.pi / float(num_proj), \
                    'projNum': num_proj, \
                    'yPos': y_pos}

        cmd_template = None

        if tomo:
            args_fmt['recoHeight'] = reco_height

            cmd_template = 'tofu tomo ' \
            '--fix-nan-and-inf ' \
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
        else:
            args_fmt['slicesPerDevice'] = slices_per_device
            args_fmt['overallAngle'] = overall_angle
            args_fmt['rollAngle'] = roll_angle
            args_fmt['laminoAngle'] = lamino_angle
            args_fmt['zParam'] = z_param
            args_fmt['paramRegion'] = param_region

            cmd_template = 'tofu lamino ' \
            '--fix-nan-and-inf ' \
            '--absorptivity ' \
            '--darks dark/ ' \
            '--flats flat/ ' \
            '--projections {projFolder}/ ' \
            '--angle {angleRad} ' \
            '--axis {axisPos},{yPos} ' \
            '--lamino-angle {laminoAngle} ' \
            '--roll-angle {rollAngle} ' \
            '--overall-angle {overallAngle} ' \
            '--slices-per-device {slicesPerDevice} ' \
            '--output slices_axis/slice-{axisPos} ' \
            '--z-parameter {zParam} ' \
            '--region="{paramRegion}" ' \
            '--number {projNum} ' \
            '--verbose'

        for rot_axis in rot_axes:
            args_fmt['axisPos'] = rot_axis

            app = cmd_template.format(**args_fmt)
            process = subprocess.Popen(app, shell=True, cwd=path)
            streamdata = process.communicate()[0]
            rc = process.returncode

            print '{0} [Axis: {1}]'.format(sample_name, rot_axis)

def start_reconstruction(search_dir, \
                         sample_names, \
                         num_axes, \
                         tomo=True, \
                         slices_per_device=None, \
                         overall_angle=None, \
                         roll_angle=None, \
                         lamino_angle=None, \
                         z_param=None, \
                         param_region=None, \
                         y_pos=None, \
                         reco_height=1):

    sample_paths = get_sample_paths(search_dir, \
                                    sample_names)

    print sample_paths
    # run_tofu(sample_paths, \
    #          num_axes=num_axes, \
    #          tomo=tomo, \
    #          slices_per_device=slices_per_device, \
    #          overall_angle=overall_angle, \
    #          roll_angle=roll_angle, \
    #          lamino_angle=lamino_angle, \
    #          z_param=z_param, \
    #          param_region=param_region, \
    #          y_pos=y_pos, \
    #          reco_height=reco_height)

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
    parser.add_argument("-l", "--lamino", \
                        help="The imaging setup is laminography", \
                        dest='tomo', \
                        action='store_false')
    parser.add_argument("-a", "--num_axes", \
                        help="The number of axes to calculate", \
                        type=int, \
                        default=40)
    parser.add_argument("-s", "--slices-per-device", \
                        help="The number of slices per device", \
                        type=int, \
                        default=10)
    parser.add_argument("-g", "--lamino-angle", \
                        help="The laminography angle", \
                        type=float, \
                        default=59.653557)
    parser.add_argument("-a", "--overall-angle", \
                        help=" The total angle over which projections were taken in degrees", \
                        type=int, \
                        default=-360)
    parser.add_argument("-a", "--roll-angle", \
                        help="The phi-misalignment angle", \
                        type=float, \
                        default=0.617746)
    parser.add_argument("-p", "--z-parameter", \
                        help="Z-axis parameter", \
                        type=str, \
                        default='z')
    parser.add_argument("-r", "--region", \
                        help="Z-axis parameter region as from,to,step", \
                        type=str, \
                        default='0,-1,1')
    parser.add_argument("-y", "--y", \
                        help="The y-position in reconstructed volume", \
                        type=int, \
                        default=None)
    parser.add_argument("-h", "--height", \
                        help="The height of reconstructed volume", \
                        type=int, \
                        default=None)

    args = parser.parse_args()

    start_reconstruction(args.search_dir, \
                         args.sample_names, \
                         args.num_axes, \
                         tomo=args.tomo, \
                         slices_per_device=args.slices_per_device, \
                         overall_angle=args.overall_angle, \
                         roll_angle=args.roll_angle, \
                         lamino_angle=args.lamino_angle, \
                         z_param=args.z_parameter, \
                         param_region=args.region, \
                         y_pos=args.y, \
                         reco_height=args.height)

if __name__ == "__main__":
    sys.exit(main())
