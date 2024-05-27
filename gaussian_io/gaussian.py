#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gaussian 16 input and output files preparation.
@author: Yu Che
"""
import re
import warnings
from pathlib import Path
from datetime import datetime, timedelta

from .header import Header
from .utils import coordinates_reader, PERIODIC_TABLE


class GaussianIn(Header):
    """
    Parser for Gaussian16 input file

    Parameters
    ----------
    in_lines: list

    """
    def __init__(self, in_lines, name=None):
        header_lines = coord_lines = []
        for index, line in enumerate(in_lines):
            if line == '\n':
                header_lines = in_lines[:index+4]
                coord_lines = in_lines[index+4:-1]
                break
        super().__init__(header_lines)
        self._coord = coordinates_reader(coord_lines, ftype='xyz')
        self._name = name

    @property
    def coord(self):
        return self._coord

    @property
    def mol_name(self):
        return self._name

    @property
    def mol_is_loaded(self):
        if len(self._coord) == 0:
            return False
        else:
            return True

    def update_mol(self, mol):
        """
        Update the molecular geometry from the given file

        Parameters
        ----------
        mol: str or list
            The path of given molecular file or
            a parsed coordinates list from GaussianOut
        Returns
        -------
        None
        """
        if isinstance(mol, (str, Path)):
            path = Path(mol)
            self._name = path.name
            assert path.suffix in ['.xyz', '.mol', '.mol2'], \
                f'Given file is not recognised, got {path.suffix}'
            coord_lines = []
            with open(path, 'r') as file:
                mol_l = file.readlines()
            if path.suffix == '.mol2':
                for idx, line in enumerate(mol_l):
                    if re.match(r' 1 [A-Z]', line):
                        coord_lines = mol_l[idx:]
                        break
            else:
                coord_lines = mol_l[2:]
            self._coord = coordinates_reader(coord_lines, ftype=path.suffix)
        elif isinstance(mol, list):
            self._coord = mol

    def to_gjf(self, path=None):
        """
        Generate the Gaussian input file for current GaussianIn object

        Parameters
        ----------
        path: str or None
            The path where the input file will be saved in.
            If None, return a list

        Returns
        -------
        input_lines: list or None
            A list of lines of generated input file
        """
        input_lines = self.get_header()
        coord_lines = []
        sum_method = ''
        for item in self.method:
            sum_method += item
        # G16 keywords geom ignore the given coordinates
        if not re.search(r'geom', sum_method, re.IGNORECASE):
            for segments in self._coord:
                coordinate_line = '{}{:>20.10f}{:>20.10f}{:>20.10f}\n'.format(
                    segments[0],
                    segments[1],
                    segments[2],
                    segments[3]
                )
                coord_lines.append(coordinate_line)
            input_lines += coord_lines
        input_lines.append('\n')
        if path is None:
            return input_lines
        else:
            in_path = Path(path)
            with open(in_path, 'w') as input_file:
                input_file.writelines(input_lines)


class GaussianOut:
    def __init__(self, out_lines, name):
        """
        Parser for Gaussian16 output file
        """
        self._name = name
        self._lines = out_lines
        self._status = dict(finished=True, error_type=False, parser=False,
                            sum_reader=False)
        self._index = dict(
            header=range(0),
            time=[],
            sum=range(0)
        )
        self._header = None
        self._summary = {}
        self._opt_steps = []
        self._freq = []
        self._cpu_time = timedelta()
        self._elapsed_time = timedelta()
        self._date = None
        # Initialise object, get error and completeness information
        if len(self._lines) < 10 or \
                not re.match(r' File| Normal', self._lines[-1]):
            self._status['finished'] = False
            warnings.warn('Unfinished Gaussian job.', UserWarning)
        else:
            error_line = self._lines[-4]
            if error_line.startswith(' Error termination'):
                self._status['error_type'] = re.findall(r'g16/(.*)\.exe',
                                                        error_line)[0]
            # If the file is a finished job and no error at the end.
            # Run the parser
            else:
                self._parser()

    @property
    def cpu_time(self):
        return self._cpu_time

    @property
    def elapsed_time(self):
        return self._elapsed_time

    @property
    def finished_date(self):
        return self._date

    @property
    def header(self):
        return self._header

    @property
    def error(self):
        return self._status['error_type']

    @property
    def finished(self):
        return self._status['finished']

    @property
    def sum_params(self):
        if not self._status['sum_reader'] and self.finished:
            self._parser_sum()
        return list(self._summary.keys())

    @property
    def coord(self):
        if not self._status['sum_reader'] and self.finished:
            self._parser_sum()
        return coordinates_reader(self._summary['coordinates'], ftype='xyz')

    def __str__(self):
        print('GaussianOut object {}'.format(self._name))
    # __repr__ = __str__

    @staticmethod
    def _time_compiler(time_line):
        time = list(map(float, re.findall(r'\d+\.?\d*', time_line)))
        format_time = timedelta(days=time[0], hours=time[1],
                                minutes=time[2], seconds=time[3])
        return format_time

    @staticmethod
    def _decider_parser(converge_lines):
        decider = {}
        for line in converge_lines:
            seg = re.split(r'\s+', line.strip())
            decider['{}_{}'.format(seg[0], seg[1])] = [float(seg[2]), seg[4]]
        return decider

    @staticmethod
    def _force_parser(line_list):
        force = []
        for item in line_list:
            if item != '\n':
                segments = re.split(r',|\s+', item.strip())
                atom = PERIODIC_TABLE[int(segments[1])]
                force.append([atom] + list(map(float, segments[-3:])))
        return force

    def _parser(self):
        """
        Parser the Header and time stamps section
        """
        assert self._status['finished'], 'Unfinished Gaussian out job.'
        # Determine header slice
        header_start, header_end, = 0, 0
        for index, line in enumerate(self._lines):
            if line.startswith(' Gaussian 16:'):
                header_start = index + 3
            elif line.startswith(' Charge = '):
                header_end = index + 1
                break
        self._index['header'] = range(header_start, header_end)
        self._parser_header()
        # Frequency calculation has an individual time stamp
        # time need to be count twice
        len_time = 1
        method = ''
        for item in self._header.method:
            method += item
        if re.search(r'freq', method, re.IGNORECASE) and \
                self._status['error_type']:
            len_time = 2
        for i in range(len(self._lines) - 1, 1, -1):
            # Finding the cpu and elapsed timeline
            if self._lines[i].startswith(' Job cpu time:'):
                self._cpu_time += self._time_compiler(self._lines[i])
                self._elapsed_time += self._time_compiler(self._lines[i + 1])
                len_time -= 1
            # Parser the date stamp
            elif re.match(r' Error| Normal', self._lines[i]):
                date = re.sub(r'\s+', '-',
                              re.findall(r'at (.*)\.', self._lines[-1])[0])
                self._date = datetime.strptime(date, '%a-%b-%d-%H:%M:%S-%Y')
            if len_time == 0:
                break
        if self.error is False:
            # Finding the summary slice
            sum_start, sum_end = 0, 0
            for index in range(len(self._lines) - 1, 1, -1):
                if self._lines[index].endswith('@\n'):
                    sum_end = index + 1
                elif self._lines[index].startswith(' 1\\1\\'):
                    sum_start = index
                    break
            self._index['sum'] = range(sum_start, sum_end)
        self._status['parser'] = True

    def _parser_header(self):
        """
        Parser header lines to a Header object
        """
        header_lines = []
        header_seg = 0
        method_line = ''
        for index in self._index['header']:
            if re.match(r'\s-+\n', self._lines[index]):
                header_seg += 1
            elif re.match(r'\s%', self._lines[index]):
                header_lines.append(self._lines[index].strip())
            elif header_seg == 1:
                method_line += self._lines[index].strip()
            elif header_seg == 3:
                header_lines += [
                    method_line, '\n', self._lines[index].strip()
                ]
            elif self._lines[index].startswith(' Charge'):
                header_lines.append('\n')
                header_lines.append(self._lines[index].strip())
                break
        self._header = Header(header_lines=header_lines)

    def _parser_sum(self):
        """
        Parser the summary section
        """
        if self._status['parser']:
            self._parser()
        assert not self.error, 'Error {} found! Cannot get summary.'.format(
            self.error
        )
        sum_line = ''
        for index in self._index['sum']:
            sum_line += self._lines[index].strip()
        sum_components = sum_line.split('\\\\')
        assert len(sum_components) >= 5
        self._summary['sys_info'] = sum_components[0]
        coordinates = sum_components[3].split('\\')
        self._summary['coordinates'] = coordinates[1:]
        rest_result = sum_components[4].split('\\')
        for item in rest_result:
            if '=' in item:
                com = item.split('=')
                self._summary[com[0]] = com[1]
        self._status['sum_reader'] = True

    def parser_optimisation(self):
        """
        Parser optimisation steps
        """
        if not self.finished:
            raise ValueError('Unfinished g16 job!')
        coordinate_start, coordinate_end, energy = 0, 0, 0
        force_start, force_end = 0, 0
        for index, line in enumerate(self._lines):
            if re.match(r' -+\n', line) and re.search(
                    r' +Input orientation:', self._lines[index - 4]
            ):
                coordinate_start = index + 1
            elif re.match(r' -+\n', line) and \
                    coordinate_start != 0 and coordinate_end == 0:
                coordinate_end = index
            if re.match(r' -+\n', line) and re.search(
                    r' +Forces ', self._lines[index - 2]
            ):
                force_start = index + 1
                force_end = force_start + (coordinate_end - coordinate_start)
            if re.match(r' SCF Done:', line):
                energy = float(re.split(r'\s+', line.strip())[4])
            if re.search(r'Converged\?', line):
                converge_lines = self._lines[index + 1: index + 5]
                step_segments = dict(
                    coord=coordinates_reader(
                        self._lines[coordinate_start: coordinate_end],
                        ftype='out'
                    ),
                    force=self._force_parser(
                        self._lines[force_start: force_end]
                    ),
                    energy=energy,
                    converge=self._decider_parser(converge_lines)
                )
                coordinate_start = coordinate_end = 0
                self._opt_steps.append(step_segments)

    def get_params(self, param=None):
        """
        Get the parameter value from the summary section

        Parameters
        ----------
        param: str
            Name of parameter
        Returns
        -------
        summary: dict
        """
        if not self._status['sum_reader']:
            self._parser_sum()
        if param is None:
            return self._summary
        else:
            return self._summary[param]

    def get_opt_step(self, step):
        """
        Get raw data of Coordinate, force, energy and converge

        Parameters
        ----------
        step: int
            Number of optimisation step

        Returns
        -------
        opt: dict
            Coordinate, force, energy and converge information
        """
        return self._opt_steps[step]
