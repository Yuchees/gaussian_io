#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gaussian 16 files io for array job on barkla.
@author: Yu Che
"""
import os
import re
import shutil
import warnings
from pathlib import Path

from .gaussian import GaussianOut, GaussianIn


def read_out(path):
    """
    Reading the Gaussian out file to a GaussianOut object

    Parameters
    ----------
    path: str
        The path of given out file

    Returns
    -------
    g16_out: GaussianOut or list of GaussianOut
        An object or a list of objects if there are links in.
    """
    out_path = Path(path)
    assert out_path.suffix == '.out', \
        'The given file is not an .out, got{} instead.'.format(out_path.suffix)
    with open(out_path, 'r') as output_file:
        lines = output_file.readlines()
    link_id = []
    # Check if there are links in this out file
    for i, line in enumerate(lines):
        if line.startswith(' Initial command:'):
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


def read_in(path):
    """
    Reading the Gaussian input file or a prepared header file to
    GaussianIn object

    Parameters
    ----------
    path: str
        The path of given input file

    Returns
    -------
    g16_in: GaussianIn or list of GaussianIn
        An object or a list of objects if there are links in.
    """
    in_path = Path(path)
    assert in_path.suffix == '.gjf', \
        'Given file must be .gjf, got {} instead.'.format(in_path.suffix)
    with open(in_path, 'r') as input_file:
        lines = input_file.readlines()
    link_id = [0]
    # Check if there are links in this input file
    for i, line in enumerate(lines):
        if re.match(r'-+link1-+\n', line, re.IGNORECASE):
            link_id.append(i)
    link_id.append(len(lines))
    # No link inside
    if len(link_id) == 2:
        return GaussianIn(in_lines=lines, name=in_path.name)
    # Link is detected
    else:
        warnings.warn(
            'There are {} of links in this input-file'.format(len(link_id) - 1),
            ResourceWarning
        )
        g16_in = []
        for j in range(len(link_id) - 1):
            g16_in.append(
                GaussianIn(in_lines=lines[link_id[j]: link_id[j + 1]],
                           name=in_path.name)
            )
        return g16_in


def write_in(gauss_in_list, path):
    in_path = Path(path)
    assert in_path.is_file(), 'Given path is not a file!'
    input_lines = []
    if isinstance(gauss_in_list, list):
        for gauss in gauss_in_list:
            input_lines += gauss.to_gjf()
            input_lines.append('--Link1--\n')
        with open(path, 'w') as input_file:
            input_file.writelines(input_lines[:-1])
    elif isinstance(gauss_in_list, GaussianIn):
        gauss_in_list.to_gjf(path=in_path)


def write_xyz(coord, xyz_path, comments):
    coord_lines = []
    for segments in coord:
        coordinate_line = '{}{:>20.10f}{:>20.10f}{:>20.10f}\n'.format(
            segments[0],
            segments[1],
            segments[2],
            segments[3]
        )
        coord_lines.append(coordinate_line)
    xyz_lines = ['{}\n'.format(len(coord)),
                 '{}\n'.format(comments)] + coord_lines
    with open(xyz_path, 'w') as mol_file:
        mol_file.writelines(xyz_lines)


# Abandoned functions
def files_distribution(path, number):
    """
    Distributed files into sub folders that can be applied for array jobs on
    barkla.

    :param path: The root folder
    :param number: The number of files in each sub-folders
    :type path: str
    :type number: int
    :return: None
    """
    # TODO: using building os function to edit path
    n, i = 0, 1
    if not path.endswith('/'):
        path = path + '/'
    j = len(os.listdir(path)) % number
    for file in os.listdir(path):
        root_path = path + file
        sub_array_path = path + str(i)
        if not os.path.exists(sub_array_path):
            os.mkdir(sub_array_path)
        shutil.move(root_path, sub_array_path)
        n += 1
        if (n == number and i != 1) or (n == (number + j) and i == 1):
            n = 0
            i += 1
    print('Distributed into {} folders.'.format((i - 1)))


def files_redistribution(path):
    """
    Collecting all sub-folders files to their root folder.

    :param path: The root folder
    :type path: str
    :return: None
    """
    if not path.endswith('/'):
        path = path + '/'
    for folder in os.listdir(path):
        file_list = os.listdir(path + str(folder))
        for file in file_list:
            target_path = '{}/{}/{}'.format(path, folder, file)
            shutil.move(target_path, path)
        os.removedirs(path + str(folder))
    print('Finished!')


if __name__ == '__main__':
    g16_in_test = read_in(path='test/header_PM7_IP_EA.gjf')
    g1 = g16_in_test[0]
    g1_gjf = g1.to_gjf()
    print('finished')
