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
    with open(out_path, 'r') as output_file:
        lines = output_file.readlines()
    return GaussianOut(out_lines=lines, name=out_path.stem)


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
    with open(xyz_path, 'w') as mol_file:
        mol_file.write(f"{len(coord)}\n")
        mol_file.write(f"{comments}\n")
        for segments in coord:
            atom_type, x, y, z = segments
            mol_file.write(f'{atom_type}'
                           f'{x:>{18-len(atom_type)}.8f}'
                           f'{y:>16.8f}'
                           f'{z:>16.8f}\n')


def files_distribution(path, number):
    """
    Distributed files into sub folders that can be applied for array jobs on
    barkla.

    Parameters
    ----------
    path: str or Path
        The root folder
    number: int
        The number of files in each sub-folders
    Returns
    -------
    None
    """
    if isinstance(path, (Path, str)):
        path = Path(path)
    else:
        raise TypeError('Given path {} is not a valid path str.'.format(path))
    n, i = 0, 1
    j = len(os.listdir(path)) % number
    for file in path.iterdir():
        sub_array_path = path / str(i)
        if not os.path.exists(sub_array_path):
            os.mkdir(sub_array_path)
        shutil.move(file, sub_array_path)
        n += 1
        if (n == number and i != 1) or (n == (number + j) and i == 1):
            n = 0
            i += 1
    print('Distributed into {} folders.'.format((i - 1)))


def files_redistribution(path):
    """
    Collecting all sub-folders files to their root folder.

    Parameters
    ----------
    path: str or Path
        The root folder
    Returns
    -------
    None
    """
    if isinstance(path, (Path, str)):
        path = Path(path)
    else:
        raise TypeError('Given path {} is not a valid path str.'.format(path))
    for folder in os.listdir(path):
        file_list = os.listdir(path / str(folder))
        for file in file_list:
            target_path = '{}/{}/{}'.format(path, folder, file)
            shutil.move(target_path, path)
        os.removedirs(path / str(folder))
    print('Finished!')
