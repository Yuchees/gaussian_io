#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gaussian 16 files io for array job on barkla.
@author: Yu Che
"""
import os
import shutil


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
