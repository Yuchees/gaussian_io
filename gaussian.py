#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gaussian 16 input and output files preparation.
@author: Yu Che
"""
import re
import warnings
from datetime import datetime, timedelta

from header import Header


class GaussianIn:
    def __init__(self):
        self.__header_status = False
        self.__header = dict(
            mem='8GB', nprocshared=2,
            Chk='/users/psyche/volatile/gaussian/',
            comments='',
            Charge=0,
            Multiplicity=1
        )

    @property
    def header_status(self):
        return self.__header_status

    @property
    def header(self):
        if self.__header_status:
            return self.__header
        else:
            raise NotImplementedError('Header has not been read or defined.')

    @header.setter
    def header(self, value):
        if type(value) == dict:
            self.__header = value
        else:
            raise TypeError('')

    @property
    def header_param(self, *args):
        if self.__header_status:
            for key in args:
                print('{:>4}: {}'.format(key, self.__header[key]))
        else:
            raise NotImplementedError('Header has not been read or defined.')

    def read(self, header_lines):
        """

        Parameters
        ----------
        header_lines: list of str

        Returns
        -------

        """
        link = []
        for line_id, line in enumerate(header_lines):
            if line.startswith('-'):
                link.append(line)

        """
        # Read static lines
        self.__header['comments'] = header_lines[-2]
        charge_multiplicity = re.split(r' +', header_lines[-1])
        self.__header['Charge'] = charge_multiplicity[2]
        self.__header['Multiplicity'] = charge_multiplicity[5]
        # Read variable lines and join them into one str
        header_line = ''
        for line in header_lines[:-2]:
            if line.startswith('%'):
                segments = re.split(r'[%=]', line)
                self.__header[segments[1]] = segments[2]
            else:
                header_line += line
        header_line = re.sub(r' # |# ', ' ', header_line)
        header_line = re.sub(r', ', ',', header_line)
        header_components = re.split(r' +', header_line)
        for param in header_components[1:]:
            if '=' in param:
                segments = re.split(r'=', param, maxsplit=1)
                self.__header[segments[0]] = segments[1]
            else:
                self.__header[param] = True
        self.__header_status = True
        """

    def write(self):
        template = [
            '%mem={}\n'.format(self.__header['mem']),
            '%nprocshared={}\n'.format(self.__header['nprocshared']),
            '%Chk={}\n'.format(self.__header['Chk'])
        ]
        param_line = '#'
        for key in self.__header.keys():
            if ((self.__header[key] is None) or
                    key in ['mem', 'Chk', 'nprocshared']):
                pass
            else:
                param_line += ' {}={}'.format(key, self.__header[key])
        param_line += '\n'
        return template


class GaussianOut:
    def __init__(self, out_lines, name):
        """
        Class for reading all Gaussian out-put file details.

        :param out_lines: list of lines from the output file
        :param name: The name of read gaussian file
        :type out_lines: list
        :type name: str
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
        if not re.match(r' File| Normal', self._lines[-1]):
            self._status['finished'] = False
            warnings.warn('Unfinished Gaussian job.', ResourceWarning)
        else:
            error_line = self._lines[-4]
            if error_line.startswith(' Error termination'):
                error = re.split(r'[/.]', error_line)[-3][1:]
                self._status['error_type'] = error
            # If the file is a finished job and no error at the end.
            # Run the parser
            else:
                self._parser()

    @property
    def cpu_time(self):
        """
        Get the time stamp

        :return: Selected time
        :rtype: datetime.timedelta
        """
        return self._cpu_time

    @property
    def elapsed_time(self):
        return self._elapsed_time

    @property
    def finished_date(self):
        return self._date

    @property
    def error(self):
        """
        Get the error type

        :return: Error bool or name
        :rtype: bool or str
        """
        return self._status['error_type']

    @property
    def finished(self):
        """
        Get the finished status

        :return: Finished bool
        :rtype: bool
        """
        return self._status['finished']

    @property
    def header(self):
        return self._header

    @property
    def version(self):
        """
        Get the Gaussian version

        :return: Version name
        :rtype: str
        """
        if not self._status['sum_reader']:
            self.parser_sum()
        return self._summary['Version']

    @property
    def sum_params(self):
        if not self._status['sum_reader']:
            self.parser_sum()
        return self._summary.keys()

    @property
    def coord(self):
        """
        Get the 3D coordinates in list

        :return: Coordinates as a list
        :rtype: list
        """
        if not self._status['sum_reader']:
            self.parser_sum()
        return self._summary['coordinates']

    def get_params(self, param=None):
        if not self._status['sum_reader']:
            self.parser_sum()
        if param is None:
            return self._summary
        else:
            return self._summary[param]

    def get_opt_step(self, step):
        return self._opt_steps[step]

    def __str__(self):
        print('GaussianOut object {}'.format(self._name))
    # __repr__ = __str__

    def _parser(self):
        """
        Parser for Gaussian 16 out put files

        :return: None
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
        self.parser_header()
        # Parser the date stamp
        date = re.sub(r'\s+', '-',
                      re.findall(r'at (.*)\.', self._lines[-1])[0])
        self._date = datetime.strptime(date, '%a-%b-%d-%H:%M:%S-%Y')
        # Frequency calculation has an individual time stamp
        # time need to be count twice
        len_time = 1
        if re.search(r'[Ff]req', self._header.method):
            len_time = 2
        for i in range(len(self._lines) - 1, 1, -1):
            # Finding the cpu and elapsed time line
            if self._lines[i].startswith(' Job cpu time:'):
                self._cpu_time += self.time_compile(self._lines[i])
                self._elapsed_time += self.time_compile(self._lines[i+1])
                len_time -= 1
            if len_time == 0:
                break
        if self._status['error_type'] is False:
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

    def parser_header(self):
        """
        Parser header lines to a Header object

        :return:
        """
        header_lines = []
        header_seg = 0
        method_line = ''
        for index in self._index['header']:
            if re.match(r' -+', self._lines[index]):
                header_seg += 1
            elif re.match(r' %', self._lines[index]):
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

    @staticmethod
    def _list_to_list_range(index_list):
        """
        Convert a list of boundaries into a list of range objects.

        :param index_list: The list contain all boundaries for ranges
        :type index_list: list
        :return: A list within range objects
        :rtype: list
        """
        assert len(index_list) > 1, 'The list contain at list 2 boundaries.'
        list_range = []
        for i in range(len(index_list) - 1):
            start = index_list[i]
            end = index_list[i + 1]
            list_range.append(range(start, end))
        return list_range

    @staticmethod
    def time_compile(time_line):
        time = list(map(float, re.findall(r'\d+\.?\d*', time_line)))
        format_time = timedelta(days=time[0], hours=time[1],
                                minutes=time[2], seconds=time[3])
        return format_time

    def parser_sum(self):
        """
        Parse the summary section

        :return: None
        """
        assert self._status['parser'], 'Run parser function first.'
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
        coordinate_start, coordinate_end, energy = 0, 0, 0
        for index, line in enumerate(self._lines):
            if re.match(r' -+\n', line) and \
                    re.search(r' +Input orientation:', self._lines[index - 4]):
                coordinate_start = index + 1
            if re.match(r' -+\n', line) and \
                    re.search(r' +Distance matrix', self._lines[index + 1]):
                coordinate_end = index
            if re.match(r' SCF Done:', line):
                energy = float(re.split(r'\s+', line.strip())[4])
            if re.search(r'Converged?', line):
                converge_lines = self._lines[index + 1: index + 5]
                step_segments = dict(
                    coord=self._lines[coordinate_start: coordinate_end],
                    energy=energy,
                    converge=converge_lines
                )
                self._opt_steps.append(step_segments)


if __name__ == '__main__':
    # Test script
    from utils import coordinates_reader, write_xyz
    with open('./test/A2_pi4.out') as file:
        lines = file.readlines()
    test_out_file = GaussianOut(out_lines=lines, name='A2_pi4')
    test_out_file.parser_sum()
    test_out_file.parser_optimisation()
    a = coordinates_reader(line_list=test_out_file.coord)
    print('Error type: ', test_out_file.error)
