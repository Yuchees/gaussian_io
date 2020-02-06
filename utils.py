#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import warnings
from pathlib import Path
from gaussian import GaussianOut
from header import Header


def read_out(path):
    out_path = Path(path)
    assert out_path.suffix is '.out', \
        'The given file is not an .out, got{} instead.'.format(out_path.suffix)
    link_id = []
    with open(out_path, 'r') as output_file:
        lines = output_file.readlines()
    # Check if there are links in this out file
    for i in range(len(lines)):
        if lines[i].startswith(' Initial command:'):
            link_id.append(i)
    link_id.append(len(lines))
    # Return an object if no link in this file
    if len(link_id) == 2:
        return GaussianOut(out_lines=lines, name=out_path.stem)
    # Return a list of object after splitting the out file
    else:
        warnings.warn(
            'There are {} of links in this out-file, '
            'return a list of GaussianOut objects'.format(len(link_id) - 1),
            ResourceWarning
        )
        g16_out = []
        for j in range(len(link_id) - 1):
            g16_out.append(
                GaussianOut(out_lines=lines[link_id[j]: link_id[j + 1]],
                            name=out_path.stem)
            )
        return g16_out


def read_in(in_path):
    name = __path_test(in_path, file_type='.gjf')
    with open(in_path, 'r') as input_file:
        lines = input_file.readlines()
    return GaussianOut(out_lines=lines, name=name)


def read_header(header_path):
    headers = []
    links = [0]
    with open(header_path, 'r') as header_file:
        lines = header_file.readlines()
    for line_id, line in enumerate(lines):
        link = 0
        if line.startswith('--'):
            links.append(line_id)
            headers.append(Header(line[links[link]: links[link+1]]))
    return headers


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


def write_xyz(coord, xyz_path, comments):
    coord_list = coordinates_reader(coord)
    coord_lines = []
    for segments in coord_list:
        coordinate_line = '{}{:>20.10f}{:>20.10f}{:>20.10f}\n'.format(
            segments[0],
            segments[1],
            segments[2],
            segments[3]
        )
        coord_lines.append(coordinate_line)
    xyz_lines = ['{}\n'.format(len(coord_list)),
                 '{}\n'.format(comments)] + coord_lines
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
    path1 = './test/A1_pi1_IPEA.out'
    a = read_out(path1)
    print('finished')
