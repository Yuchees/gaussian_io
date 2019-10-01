#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gaussian 16 input and output files preparation.
@author: Yu Che
"""
import re
import datetime
import warnings


class Header(object):
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


class GaussianOut(Header):
    def __init__(self, out_lines, name):
        """
        Class for reading all Gaussian out-put file details.

        :param out_lines: list of lines from the output file
        :param name: The name of read gaussian file
        :type out_lines: list
        :type name: str
        """
        super().__init__()
        self.__name = name
        self.__lines = out_lines
        self.__len = len(self.__lines)
        self.status = dict(finished=True, error_type=False, basis_parser=False,
                           sum_reader=False)
        self.__link_range = []
        self.__index = []
        self.__summary = []
        self.__opt_steps = []
        self.__freq = []
        self.__cpu_time = []
        self.__elapsed_time = []
        # Initialise object, get error and completeness information
        if not re.match(r' File| Normal', self.__lines[-1]):
            self.status['finished'] = False
            warnings.warn('Unfinished Gaussian job.', ResourceWarning)
        else:
            error_line = self.__lines[-4]
            if error_line.startswith(' Error termination'):
                error = re.split(r'[/.]', error_line)[-3][1:]
                self.status['error_type'] = error

    @property
    def time(self, link=0, time_type='cpu'):
        """
        Get the time stamp

        :param link: The number of link
        :param time_type: The name of time stamp, must be 'cpu' or 'elapsed'
        :type link: int
        :type time_type: str
        :return: Selected time
        :rtype: datetime.timedelta
        """
        assert \
            time_type in ['cpu', 'elapsed'], 'Time type must be cpu or elapsed.'
        time = None
        if not self.status['sum_reader']:
            self.parser_cpu_time()
        if time_type == 'cpu':
            time = self.__cpu_time[link]
        elif time_type == 'elapsed':
            time = self.__elapsed_time[link]
        return time

    @property
    def error(self):
        """
        Get the error type

        :return: Error bool or name
        :rtype: bool or str
        """
        return self.status['error_type']

    @property
    def finished(self):
        """
        Get the finished status

        :return: Finished bool
        :rtype: bool
        """
        return self.status['finished']

    @property
    def version(self):
        """
        Get the Gaussian version

        :return: Version name
        :rtype: str
        """
        if not self.status['sum_reader']:
            self.parser_sum()
        return self.__summary[0]['Version']

    @property
    def sum_params(self):
        if not self.status['sum_reader']:
            self.parser_sum()
        return self.__summary[0].keys()

    def final_coordinates(self, link=0):
        """
        Get the 3D coordinates in list

        :param link: The number of link
        :type link: int
        :return: Coordinates as a list
        :rtype: list
        """
        if not self.status['sum_reader']:
            self.parser_sum()
        return self.__summary[link]['coordinates']

    def final_params(self, param, link=0):
        if not self.status['sum_reader']:
            self.parser_sum()
        res = self.__summary[link][param]
        return res

    def __str__(self):
        print('GaussianOut object {}'.format(self.__name))
    # __repr__ = __str__

    def header_reader(self):
        """


        :return:
        """
        assert self.status['parser'], 'Run parser function first.'
        i = 0
        for link_index in self.__index:
            header_lines = []
            header_section = False
            for index in link_index['header']:
                if re.match(r' -+', self.__lines[index]):
                    header_section = not header_section
                elif re.match(r' %', self.__lines[index]) or header_section:
                    header_lines.append(self.__lines[index].strip())
                elif self.__lines[index].startswith(' Charge'):
                    header_lines.append(self.__lines[index].strip())
                    break
            self.read(header_lines=header_lines)
            i += 1

    @staticmethod
    def __list_to_list_range(index_list):
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

    def parser(self, opt=False, freq=False):
        """
        Parser for Gaussian 16 out put files

        :param opt: whether to read the optimisation steps
        :param freq: weather to read the frequency calculation
        :type opt: bool
        :type freq: bool
        :return: None
        """
        assert self.status['finished'], 'Unfinished Gaussian out job.'
        # Determine link position
        link_list = []
        for index in range(self.__len):
            if self.__lines[index].startswith(' Initial command:'):
                link_list.append(index)
        link_list.append(self.__len)
        self.__link_range = self.__list_to_list_range(link_list)
        link = 0
        # Slice different component for each link
        for link_range in self.__link_range:
            self.__index.append({})
            header_start, header_end, time_start, time_end = 0, 0, 0, 0
            # Determine header slice
            for index in link_range:
                if self.__lines[index].startswith(' Gaussian 16:'):
                    header_start = index + 3
                elif self.__lines[index].startswith(' Charge = '):
                    header_end = index + 1
                    break
            self.__index[link]['header'] = range(header_start, header_end)
            # Determine time stamp slice
            self.__index[link]['time'] = []
            for index in range(link_range[-1], link_range[0] - 1, -1):
                # Frequency calculation has an individual time stamp
                if freq:
                    if len(self.__index[link]['time']) == 2:
                        break
                else:
                    if len(self.__index[link]['time']) == 1:
                        break
                if self.__lines[index].startswith(' Job cpu time:'):
                    time_start, time_end = index, index + 2
                    self.__index[link]['time'].append(
                        range(time_start, time_end)
                    )
            link += 1
        # Slice each step if the Gaussian job does not raise an error
        if not self.status['error_type']:
            link = 0
            for link_range in self.__link_range:
                # Determine the summary slice
                sum_start, sum_end = 0, 0
                for index in range(link_range[-1], link_range[0] - 1, -1):
                    if self.__lines[index].endswith('@\n'):
                        sum_end = index + 1
                    elif self.__lines[index].startswith(' 1\\1\\'):
                        sum_start = index
                        break
                self.__index[link]['sum'] = range(sum_start, sum_end)
                # Determine each optimisation step slice
                if opt:
                    liter_list = []
                    for index in link_range:
                        if re.match(
                                r' +Input orientation: +',
                                self.__lines[index]
                        ):
                            liter_list.append(index)
                        elif self.__lines[index].startswith(
                                ' Optimization completed.'
                        ):
                            liter_list.append(index + 1)
                            break
                    self.__index[link]['opt_steps'] = \
                        self.__list_to_list_range(liter_list)
                link += 1
        self.status['parser'] = True

    def parser_sum(self):
        """
        Parse the summary section

        :return: None
        """
        assert self.status['parser'], 'Run parser function first.'
        for i in range(len(self.__link_range)):
            self.__summary.append({})
            sum_line = ''
            for index in self.__index[i]['sum']:
                sum_line += self.__lines[index].strip()
            sum_components = sum_line.split('\\\\')
            assert len(sum_components) >= 5
            self.__summary[i]['sys_info'] = sum_components[0]
            coordinates = sum_components[3].split('\\')
            self.__summary[i]['coordinates'] = coordinates[1:]
            rest_result = sum_components[4].split('\\')
            for item in rest_result:
                if '=' in item:
                    com = item.split('=')
                    self.__summary[i][com[0]] = com[1]
        self.status['sum_reader'] = True

    def parser_cpu_time(self):
        """
        Parse the CPU time section

        :return: None
        """
        assert self.status['parser'], 'Run parser function first.'

        def time_compile(time_line):
            time = list(map(float, re.findall(r'\d+\.?\d*', time_line)))
            format_time = datetime.timedelta(
                days=time[0], hours=time[1],
                minutes=time[2], seconds=time[3]
            )
            return format_time

        for link_index in self.__index:
            for index in link_index['time']:
                self.__cpu_time.append(time_compile(self.__lines[index[0]]))
                self.__elapsed_time.append(time_compile(self.__lines[index[1]]))

    def parser_optimisation(self, link=0):
        for step in self.__index[link]['opt_steps']:
            step_segnment = []
            first_atom_index = step[0] + 4
            # TODO: optimisation
        pass

    def freq_reader(self):
        """
        Parse the frequency section

        :return: None
        """
        # TODO: frequency reader function
        pass


if __name__ == '__main__':
    # Test script
    with open('./test/A2_pi4.out') as file:
        lines = file.readlines()
    test_out_file = GaussianOut(out_lines=lines, name='A2_pi4')
    test_out_file.parser(opt=True)
    test_out_file.parser_sum()
    test_out_file.header_reader()
    test_out_file.parser_cpu_time()
    test_out_file.final_params(param='HF')
    print('Error type: ', test_out_file.error)
