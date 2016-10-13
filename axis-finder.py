import os
import sys
import argparse
import importlib
import ast
import logging
import subprocess
import numpy as np
from skimage import io

def get_sample_entries(search_dir, sample_confs, tomo_folder='tomo'):
    out = []

    for root, dirs, files in os.walk(search_dir):
        comps = root.split(os.sep)
        for sample_name, axis in sample_confs.iteritems():
            if tomo_folder in os.path.basename(root) and sample_name in comps:
               out.append({'name': sample_name, 'path': root, 'axis': axis})

    return out

def run_tofu(sample_entries, \
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
             reco_height=1, \
             output_folder='slices', \
             output_axis_folder='slices_axis'):

    def run_process(cmd_template, args, working_path):
        app = cmd_template.format(**args)
        print app
        process = subprocess.Popen(app, shell=True, cwd=working_path)
        streamdata = process.communicate()[0]
        #print app

    for i, sample_entry in enumerate(sample_entries):
        path = sample_entry['path']
        sample_name = sample_entry['name']

        proj_path = os.path.join(path, proj_folder)
        projs = [f for f in os.listdir(proj_path) \
                 if os.path.isfile(os.path.join(proj_path, f))]

        data = io.imread(os.path.join(proj_path, projs[0]))
        height, width = data.shape
        hc,wc = int(height/2), int(width/2)

        axis_is_container, axis_is_number = \
                isinstance(sample_entry['axis'], tuple) or \
                isinstance(sample_entry['axis'], list), \
                isinstance(sample_entry['axis'], int) or \
                isinstance(sample_entry['axis'], float)

        if axis_is_container:
            wc = sample_entry['axis'][0]
        elif axis_is_number:
            wc = sample_entry['axis']
        else:
            raise ValueError('The axis has incorrect type.')

        rot_axes = None
        if num_axes:
            rot_axes = range(wc-num_axes, wc+num_axes+1)

        if y_pos is None:
            y_pos = hc

        num_proj = len(projs) - 1
        args_fmt = {'projFolder': proj_folder, \
                    'angleRad': 2 * np.pi / float(num_proj), \
                    'projNum': num_proj}

        cmd_template = None

        if tomo:
            args_fmt['recoHeight'] = reco_height
            args_fmt['yPos'] = y_pos

            cmd_template = 'tofu tomo ' \
            '--fix-nan-and-inf ' \
            '--absorptivity ' \
            '--darks dark/ ' \
            '--flats flat/ ' \
            '--projections {projFolder}/ ' \
            '--angle {angleRad} ' \
            '--axis {axisPos} ' \
            '--method fbp ' \
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

            if axis_is_container:
                args_fmt['yPos'] = sample_entry['axis'][1]
            else:
                args_fmt['yPos'] = hc

            cmd_template = 'tofu lamino ' \
            '--fix-nan-and-inf ' \
            '--absorptivity ' \
            '--darks dark/ ' \
            '--flats flat/ ' \
            '--projections {projFolder}/ ' \
            '--angle {angleRad} ' \
            '--lamino-angle {laminoAngle} ' \
            '--roll-angle {rollAngle} ' \
            '--overall-angle {overallAngle} ' \
            '--slices-per-device {slicesPerDevice} ' \
            '--z-parameter {zParam} ' \
            '--region="{paramRegion}" ' \
            '--number {projNum} ' \
            '--verbose'

            if axis_is_container:
                cmd_template += ' --axis "{axisPos},{yPos}"'
            elif axis_is_number:
                cmd_template += ' --axis "{axisPos},{yPos}"'
            else:
                raise ValueError('The axis has incorrect value.')

        if num_axes:
            cmd_template += ' --output {outAxisSlicesFolder}/slice-{axisPos}-%05i.tif' \
                                if tomo else \
                                    ' --output {outAxisSlicesFolder}/slice-{axisPos}'
        else:
            cmd_template += ' --output {outSlicesFolder}/slice-%05i.tif' \
                                if tomo else \
                                    ' --output {outSlicesFolder}/slice'

        args_fmt['outSlicesFolder'] = output_folder
        args_fmt['outAxisSlicesFolder'] = output_axis_folder

        if rot_axes is not None:
            for rot_axis in rot_axes:
                args_fmt['axisPos'] = rot_axis

                run_process(cmd_template, args_fmt, path)

                print '{0} [Axis: {1}]'.format(sample_name, rot_axis)
        else:
            args_fmt['axisPos'] = wc
            run_process(cmd_template, args_fmt, path)

def start_reconstruction(search_dir, \
                         sample_confs, \
                         num_axes, \
                         tomo=True, \
                         slices_per_device=None, \
                         overall_angle=None, \
                         roll_angle=None, \
                         lamino_angle=None, \
                         z_param=None, \
                         param_region=None, \
                         y_pos=None, \
                         reco_height=1, \
                         output_folder='slices', \
                         output_axis_folder='slices_axis'):

    sample_entries = get_sample_entries(search_dir, sample_confs)

    run_tofu(sample_entries, \
             num_axes=num_axes, \
             tomo=tomo, \
             slices_per_device=slices_per_device, \
             overall_angle=overall_angle, \
             roll_angle=roll_angle, \
             lamino_angle=lamino_angle, \
             z_param=z_param, \
             param_region=param_region, \
             y_pos=y_pos, \
             reco_height=reco_height, \
             output_folder=output_folder, \
             output_axis_folder=output_axis_folder)

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

    parser.add_argument("--search_dir", \
                        help="Path to the folder containing the splitted data of samples", \
                        type=str, \
                        required=True)
    parser.add_argument("--sample-configs", \
                        help="List of sample entries as dictionaries {name: axis_x,axis_y} or {name: axis_x} to process", \
                        type=_tryeval, \
                        required=True)
    parser.add_argument("--lamino", \
                        help="The imaging setup is laminography", \
                        dest='tomo', \
                        action='store_false')
    parser.add_argument("--num_axes", \
                        help="The number of axes to calculate", \
                        type=int, \
                        default=40)
    parser.add_argument("--slices-per-device", \
                        help="The number of slices per device", \
                        type=int, \
                        default=10)
    parser.add_argument("--lamino-angle", \
                        help="The laminography angle", \
                        type=float, \
                        default=59.653557)
    parser.add_argument("--overall-angle", \
                        help=" The total angle over which projections were taken in degrees", \
                        type=int, \
                        default=-360)
    parser.add_argument("--roll-angle", \
                        help="The phi-misalignment angle", \
                        type=float, \
                        default=0.617746)
    parser.add_argument("--z-parameter", \
                        help="Z-axis parameter", \
                        type=str, \
                        default='z')
    parser.add_argument("--region", \
                        help="Z-axis parameter region as from,to,step", \
                        type=str, \
                        default='0,1,1')
    parser.add_argument("--y", \
                        help="The y-position in reconstructed volume", \
                        type=int, \
                        default=None)
    parser.add_argument("--height", \
                        help="The height of reconstructed volume", \
                        type=int, \
                        default=None)
    parser.add_argument("--output-folder", \
                        help="The name of the output folder of the reconstruction", \
                        type=str, \
                        default='slices')
    parser.add_argument("--output-axis-folder", \
                        help="The name of the output folder of slices of found rotation axes", \
                        type=str, \
                        default='slices_axis')

    args = parser.parse_args()

    start_reconstruction(args.search_dir, \
                         args.sample_configs, \
                         args.num_axes, \
                         tomo=args.tomo, \
                         slices_per_device=args.slices_per_device, \
                         overall_angle=args.overall_angle, \
                         roll_angle=args.roll_angle, \
                         lamino_angle=args.lamino_angle, \
                         z_param=args.z_parameter, \
                         param_region=args.region, \
                         y_pos=args.y, \
                         reco_height=args.height, \
                         output_folder=args.output_folder, \
                         output_axis_folder=args.output_axis_folder)

if __name__ == "__main__":
    sys.exit(main())
