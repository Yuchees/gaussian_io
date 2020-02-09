#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gaussian 16 input and output files preparation.
@author: Yu Che
"""

import re


class Header:
    """
    Parser for Gaussian16 input and output file header section

    Parameters
    ----------
    header_lines: list

    Attributes
    ----------
    sys: dict
    method: str
    comments: str
    charge: int
    multiplicity: {1, 2}

    """
    def __init__(self, header_lines):
        self.sys = {}
        self.method = ''
        self.comments = ''
        self.charge = 0
        self.multiplicity = 1
        self._read_header(header_lines)

    @staticmethod
    def _sys_line(key, value):
        return '%{}={}\n'.format(key, value)

    @staticmethod
    def _method_line(method):
        return '# {}\n'.format(method)

    def _read_header(self, job_lines):
        """
        Parse the header lines

        Parameters
        ----------
        job_lines: list of str

        Returns
        -------

        """
        method = ''
        for line_id, line in enumerate(job_lines):
            if line.startswith('%'):
                key, value = line[1:-1].split('=')
                self.sys[key] = value
            elif line.startswith('#'):
                method += line.strip()
            elif line == '\n':
                self.comments = job_lines[line_id + 1].strip()
                charge, mult = re.findall(r'-?\d+', job_lines[line_id+3])
                self.method = re.split(r'#\s?', method)[1:]
                self.charge = int(charge)
                self.multiplicity = int(mult)
                break

    def get_header(self):
        """
        Generate the header information to a standard Gaussian input file

        Returns
        -------
        list:
            A list of input file lines
        """
        header_lines = []
        for key, value in self.sys.items():
            header_lines.append(self._sys_line(key, value))
        for item in self.method:
            header_lines.append(self._method_line(item))
        comments_lines = ['\n',
                          '{}\n'.format(self.comments),
                          '\n',
                          '{} {}\n'.format(self.charge, self.multiplicity)]
        header_lines += comments_lines
        return header_lines


if __name__ == '__main__':
    with open('test/header_PM7_IP_EA.gjf', 'r') as file:
        lines = file.readlines()
    h = Header(lines)
    d = h.get_header()
    print('finished')
