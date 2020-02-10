#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re


def coordinates_reader(line_list, ftype='out'):
    period_table = {'1': 'H', '3': 'Li', '5': 'B', '6': 'C', '7': 'N',
                    '8': 'O', '9': 'F', '11': 'Na', '15': 'P',
                    '16': 'S', '17': 'Cl', '35': 'Br', '53': 'I'}
    coordinates = []
    for item in line_list:
        if item != '\n':
            segments = re.split(r',|\s+', item.strip())
            if ftype == 'out':
                atom = period_table[segments[1]]
                pos = list(map(float, segments[-3:]))
            elif ftype == '.mol2':
                atom = re.sub(r'[0-9]+', '', segments[1])
                pos = list(map(float, segments[2:5]))
            else:
                atom = segments[0]
                pos = list(map(float, segments[-3:]))
            coordinates.append([atom] + pos)
    return coordinates


if __name__ == '__main__':
    pass
