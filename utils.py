#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
from .gaussian_read import GaussianOut


def read_out(out_path):
    name = __path_test(out_path, file_type='.out')
    with open(out_path, 'r') as output_file:
        lines = output_file.readlines()
    mol = GaussianOut(out_lines=lines, name=name)
    return mol


def read_in(in_path):
    name = __path_test(in_path, file_type='.gjf')
    with open(in_path, 'r') as input_file:
        lines = input_file.readlines()
    return GaussianOut(out_lines=lines, name=name)


def __path_test(test_path, file_type):
    os.stat(test_path)
    name = os.path.basename(test_path)
    if os.path.splitext(test_path)[1] != file_type:
        raise AttributeError(
            '{} is not a gaussian {} file.'.format(name, file_type)
        )
    return name


def coordinates_reader(line_list):
    period_table = {'1': 'H', '3': 'Li', '6': 'C', '7': 'N',
                    '8': 'O', '9': 'F', '11': 'Na', '15': 'P',
                    '16': 'S', '17': 'Cl', '35': 'Br', '53': 'I'}
    coordinates = []
    for item in line_list:
        segments = re.split(r',|\s+', item)
        if len(segments) != 4:
            atom = period_table[segments[2]]
            pos = list(map(float, segments[-4:-1]))
        else:
            atom = segments[0]
            pos = list(map(float, segments[-3:]))
        coordinates.append([atom] + pos)
    return coordinates


def write_xyz(out_put_coordinates, xyz_path, comments):
    coordinates_list = coordinates_reader(out_put_coordinates)
    coordinate_lines = []
    for segments in coordinates_list:
        coordinate_line = '{}{:>20.10f}{:>20.10f}{:>20.10f}\n'.format(
            segments[0],
            segments[1],
            segments[2],
            segments[3]
        )
        coordinate_lines.append(coordinate_line)
    xyz_lines = ['{}\n'.format(len(coordinates_list)),
                 '{}\n'.format(comments)] + coordinate_lines
    with open(xyz_path, 'w') as mol_file:
        mol_file.writelines(xyz_lines)


"""def read_write_all(path):
    files_list = os.listdir(path)
    for file in files_list:
        file_path = path + '/' + file
        out_put = read_out(file_path)
        out_put.parser(freq=True)
        xyz = out_put.final_coordinates
        hf = out_put.final_params('HF')
        xyz_path = os.path.dirname(path) + '/dyes_tetramer_xyz/' + file
        xyz_path2 = os.path.splitext(xyz_path)[0] + '.xyz'
        write_xyz(out_put_coordinates=xyz, xyz_path=xyz_path2, comments=hf)
"""

if __name__ == '__main__':
    # path = '../../dye_copolymer/test/output_PM7_opt/dyes_tetramer/dyes_tetramer_out/D10_A12_pi5_An3.out'
    path = '../../../SSD/output_PM7_opt/dyes_tetramer/dyes_tetramer_out'
    # read_write_all(path)
    print('finished')
