#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Utilities for reading and writing Gaussian input/output files."""

import os
import re
import shutil
import warnings
from pathlib import Path

from .gaussian import GaussianOut, GaussianIn


def read_out(path):
    """
    Read a Gaussian ``.out`` file and return a parsed object.

    Parameters
    ----------
    path: str or Path
        Path to the Gaussian output file.

    Returns
    -------
    GaussianOut
        Parsed Gaussian output object.

    Raises
    ------
    FileNotFoundError
        If the specified file does not exist.
    """
    out_path = Path(path)
    if not out_path.is_file():
        raise FileNotFoundError(f'File {out_path} does not exist.')
    with open(out_path, 'r') as output_file:
        lines = output_file.readlines()
    return GaussianOut(out_lines=lines, name=out_path.stem)


def read_in(path):
    """
    Read a Gaussian input file (.gjf). Supports single or multi-link sections.

    Parameters
    ----------
    path : str or Path
        Path to the Gaussian input file.

    Returns
    -------
    GaussianIn or list of GaussianIn
        Single parsed input object, or list if multiple link sections detected.

    Raises
    ------
    ValueError
        If the file extension is not .gjf.
    FileNotFoundError
        If the input file does not exist.
    """
    in_path = Path(path)
    if in_path.suffix != '.gjf':
        raise ValueError(
            f'Given file must be .gjf, got {in_path.suffix} instead.'
        )
    if not in_path.is_file():
        raise FileNotFoundError(f'Input file {in_path} does not exist.')

    with open(in_path, 'r') as input_file:
        lines = input_file.readlines()
    link_id = [0]
    # Check if the file contains multiple link sections
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
    """
    Write one or more :class:`GaussianIn` objects to a ``.gjf`` file.

       Parameters
       ----------
       gauss_in_list : GaussianIn or list[GaussianIn]
           Object(s) to be written.
       path : str or Path
           Destination file path.
       """
    in_path = Path(path)
    if in_path.suffix != '.gif':
        raise ValueError(
            f'Output path must be a .gjf file, got {in_path.suffix} instead.'
        )
    input_lines = []
    if isinstance(gauss_in_list, list):
        for gauss in gauss_in_list:
            input_lines += gauss.to_gjf()
            input_lines.append('--Link1--\n')
        with open(in_path, 'w') as input_file:
            input_file.writelines(input_lines[:-1])
    elif isinstance(gauss_in_list, GaussianIn):
        gauss_in_list.to_gjf(path=in_path)
    else:
        raise TypeError(
            "gauss_in_list must be a GaussianIn instance or a list thereof"
        )


def write_xyz(coord, xyz_path, comments):
    """
    Write atomic coordinates to an XYZ formatted file.

    Parameters
    ----------
    coord : sequence of (str, float, float, float)
        List of tuples: atomic symbol and x, y, z coordinates.
    xyz_path : str or Path
        Destination file path (.xyz).
    comments : str, optional
        Comment line to include after atom count.
    """
    xyz_path = Path(xyz_path)
    with open(xyz_path, 'w') as mol_file:
        mol_file.write(f'{len(coord)}\n')
        mol_file.write(f'{comments}\n')
        for segments in coord:
            atom_type, x, y, z = segments
            mol_file.write(f'{atom_type}'
                           f'{x:>{18-len(atom_type)}.8f}'
                           f'{y:>16.8f}'
                           f'{z:>16.8f}\n')


def files_distribution(root, per_folder):
    """
    Distribute files from a directory into subfolders for array jobs.

    Parameters
    ----------
    root : str or Path
        Root directory containing files to distribute.
    per_folder : int
        Maximum number of files per subfolder.

    Raises
    ------
    TypeError
        If root is not a valid path or per_folder is not positive.
    """
    root = Path(root)
    if not root.is_dir():
        raise TypeError(f'Root path must be a directory: {root}')
    if per_folder <= 0:
        raise ValueError('per_folder must be a positive integer.')
    n, i = 0, 1
    j = len(os.listdir(root)) % per_folder
    for file in root.iterdir():
        sub_array_path = root / str(i)
        if not os.path.exists(sub_array_path):
            os.mkdir(sub_array_path)
        shutil.move(file, sub_array_path)
        n += 1
        if (n == per_folder and i != 1) or (n == (per_folder + j) and i == 1):
            n = 0
            i += 1
    print('Distributed into {} folders.'.format((i - 1)))


def files_redistribution(root):
    """
    Move files from all subdirectories back to the root directory.

    Parameters
    ----------
    root : str or Path
        Root directory containing subfolders.

    Raises
    ------
    TypeError
        If root is not a valid path.
    """
    root = Path(root)
    if not root.is_dir():
        raise TypeError(f'Root path must be a directory: {root}')

    for folder in [f for f in root.iterdir() if f.is_dir()]:
        for file in folder.iterdir():
            shutil.move(str(file), root)
        folder.rmdir()
    print("Redistribution complete.")
