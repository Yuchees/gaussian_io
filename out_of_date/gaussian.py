#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gaussian 16 input and output files preparation.
@author: Yu Che
"""
import os
import shutil
import re
from datetime import datetime


# noinspection PyMethodMayBeStatic
class GaussianIO:
    """
    Gaussian 16 input and output files preparation function.
    """
    def __init__(self, method, mol, seq, root_path='../../SSD'):
        """
        :param method: DFT method
        :param mol: Molecule name
        :param seq: Sequence type
        :param root_path: The root path for input and output files
        :type method: str
        :type mol: str
        :type seq: str
        """
        self.gauss_method = method
        self.elements = {1: 'H', 6: 'C', 7: 'N', 8: 'O', 9: 'F', 15: 'P',
                         16: 'S', 17: 'Cl', 35: 'Br', 53: 'I'}
        self.mol_name = '{}_{}'.format(mol, seq)
        # Gaussian16 header and barkla bash template
        self.header = './header_{}'.format(method)
        self.bash = './bash_template'
        # Molecular coordinators
        self.mol_origin = '{}/{}/{}'.format(root_path, mol, seq)
        # Gaussian16 input and output folder
        self.input_folder = '{}/input_{}/{}'.format(
            root_path, method, self.mol_name)
        self.output_folder = '{}/output_{}/{}'.format(
            root_path, method, self.mol_name)
        self.origin_result_folder = ('{}/result'.format(self.output_folder))
        # Normal terminated results folder
        self.normal_result_folder = (
                self.output_folder + '/{}_out'.format(self.mol_name)
        )
        # Molecule structure folder
        self.mol_result = self.output_folder + '/{}_xyz'.format(self.mol_name)
        self.chk_path = (
            '%Chk=/users/psyche/volatile/gaussian/chk/{}/'.format(method)
        )
        if not os.path.exists(self.input_folder):
            os.makedirs(self.input_folder)
        if not os.path.exists(self.origin_result_folder):
            os.makedirs(self.origin_result_folder)
        if not os.path.exists(self.normal_result_folder):
            os.makedirs(self.normal_result_folder)
        if not os.path.exists(self.mol_result):
            os.makedirs(self.mol_result)

    def info(self, info):
        """
        Print variables for different function.

        :param info: One of 'all', 'input', 'neg', 'error' and 'error_input'.
        :type info: str
        :return: None
        """
        if info in ['all']:
            print('Gaussian16 {}'.format(self.gauss_method))
        if info in ['all', 'input']:
            print(
                'Header template:    {}\n'
                'Checkpoint line:    {}\n'
                'Molecular folder:   {}\n'
                'Gaussian input:     {}/{}'.format(
                    self.header,
                    self.chk_path,
                    self.mol_origin,
                    self.input_folder,
                    self.mol_name
                )
            )
        if info in ['all', 'neg', 'error']:
            print(
                'HPC results folder: {}\n'
                'Normal output:      {}'.format(
                    self.origin_result_folder,
                    self.normal_result_folder
                )
            )
        if info in ['all', 'error_input']:
            print(
                'Error input folder: {}\n'
                'Error check folder: {}'.format(
                    self.input_folder + '/error...',
                    self.output_folder + '/error...'
                )
            )
        if info not in ['all', 'input', 'neg', 'error', 'error_input']:
            print(
                'The info variable must belong to: all, input, neg, error,'
                'error_input.'
            )

    def prep_input(self, geometry):
        """
        Generate gaussian input files.\n
        All chemical files must be stored under self.input_folder.\n
        Header information is read from self.header file.\n
        Checkpoint file path is read from self.chk_path variable and named
        as same as the molecule file.

        :return: None
        """
        print('Processing...')
        start = datetime.now()
        # Create folders for origin Gaussian input files
        input_origin_folder = self.input_folder + '/{}'.format(self.mol_name)
        if not os.path.exists(input_origin_folder):
            os.makedirs(input_origin_folder)
        with open(self.header, 'r') as header:
            template = header.readlines()
        # Generate Gaussian input data for all molecules
        for file in os.listdir(self.mol_origin):
            input_data = template.copy()
            # Get the molecular name
            name = file.split('.')[0]
            # Edit the checkpoint line
            for i in range(len(input_data)):
                if input_data[i].startswith('%Chk'):
                    input_data[i] = self.chk_path + '{}.chk\n'.format(name)
            # Read molecule file
            if geometry == 'local':
                molecular_file = self.mol_origin + '/' + file
                with open(molecular_file, 'r') as data:
                    # Get all atoms coordinates
                    # Mol format
                    if file.endswith('.mol'):
                        for line in data:
                            segments = re.split(r'\s+', line)
                            try:
                                if segments[4] in self.elements.values():
                                    xyz_line = '{}{:>14}{:>14}{:>14}\n'.format(
                                        segments[4],
                                        segments[1],
                                        segments[2],
                                        segments[3]
                                    )
                                    input_data.append(xyz_line)
                            except IndexError:
                                pass
                    # XYZ format
                    elif file.endswith('.xyz'):
                        for line in data:
                            try:
                                if line[0].isalpha():
                                    input_data.append(line)
                            except IndexError:
                                pass
                    else:
                        print('Waring!\n'
                              '{} is not MOL or XYZ format!'.format(file))
                        break
                # Adding terminate line
                input_data.append('\n')
            elif geometry == 'chk':
                geom_line = False
                for line in input_data:
                    if line.startswith('# Geom'):
                        geom_line = True
                if not geom_line:
                    input_data.insert(4, '# Geom=Checkpoint Guess=Read\n')
            else:
                print('Error! Geometry must be local or chk.')
            # Writing data into a gjf file
            input_path = '{}/{}.gjf'.format(input_origin_folder, name)
            with open(input_path, 'w') as input_file:
                input_file.writelines(input_data)
        print('Finished. Total time:{}'.format(datetime.now() - start))

    def error_screening(self):
        """
        Checking the output files and distributing unfinished amd error files
        into different folder.\n
        Error folders are automatically created and named by the error type.

        :return: None
        """
        # Checking the error for output files
        print('Targeted folder: {}'.format(self.origin_result_folder))
        start = datetime.now()
        i, j = 0, 0
        error_type = []
        for file in os.listdir(self.origin_result_folder):
            if not file.endswith('.out'):
                print('Error!\n{} is not a Gaussian out file!'.format(file))
                break
            path = self.origin_result_folder + '/' + file
            with open(path, 'r') as gauss_out:
                lines = gauss_out.readlines()
                # Checking the ending line
                if not re.match(r' File| Normal', lines[-1]):
                    unfinished = self.output_folder + '/unfinished'
                    if not os.path.exists(unfinished):
                        os.mkdir(unfinished)
                    shutil.move(path, unfinished)
                    i += 1
                else:
                    error_line = lines[-4:-3][0]
                    # Checking the error indicator
                    if error_line.startswith(' Error termination'):
                        error = re.split(r'[/.]', error_line)[-3][1:]
                        if error not in error_type:
                            error_type.append(error)
                        # Creating a new folder for different error type
                        error_folder = self.output_folder + '/error_' + error
                        if not os.path.exists(error_folder):
                            os.mkdir(error_folder)
                        shutil.move(path, error_folder)
                        j += 1
        print(
            'Finished.\n'
            'Unfinished:             {}\n'
            'Error result:           {}\n'
            'Error categories:       {}\n'
            'Total time:{}'.format(i, j, error_type, (datetime.now() - start))
        )

    def neg_freq_screening(self):
        """
        Checking the frequency information and distributing negative frequency
        output files into 'neg_freq' folder.

        :return: None
        """
        print('Targeted folder: {}'.format(self.origin_result_folder))
        start = datetime.now()
        i, j = 0, 0
        for file in os.listdir(self.origin_result_folder):
            if not file.endswith('.out'):
                print('Error!\n{} is not a Gaussian out file!'.format(file))
                break
            path = self.origin_result_folder + '/' + file
            with open(path, 'r') as gauss_out:
                for line in gauss_out:
                    # Checking the frequencies
                    if line.startswith(' Frequencies'):
                        data = re.split(r'\s+', line)
                        # Normal terminated jobs
                        if float(data[3]) > 0:
                            shutil.move(path, self.normal_result_folder)
                            i += 1
                            break
                        # Negative frequencies
                        elif float(data[3]) < 0:
                            neg_folder = self.output_folder + '/neg_freq'
                            if not os.path.exists(neg_folder):
                                os.mkdir(neg_folder)
                            shutil.move(path, neg_folder)
                            j += 1
                            break
        print(
            'Finished.\n'
            'Normal results:            {}\n'
            'Negative frequency result: {}\n'
            'Total time:{}'.format(i, j, (datetime.now() - start))
        )

    def prep_error_input(self, error):
        """
        Generating input files for error and negative frequency results.
        Using prepared header information.

        :return: None
        """
        error_folder = self.output_folder + '/{}'.format(error)
        print('Targeted folder: {}'.format(error_folder))
        start = datetime.now()
        error_list = os.listdir(error_folder)
        with open(self.header, 'r') as header:
            template = header.readlines()
        for file in error_list:
            input_data = template.copy()
            name = file.split('.')[0]
            geom_line = False
            # Edit checkpoint line
            for i in range(len(input_data)):
                if input_data[i].startswith('%Chk'):
                    input_data[i] = self.chk_path + '{}.chk\n'.format(name)
                elif input_data[i].startswith('# Geom'):
                    geom_line = True
            if not geom_line:
                input_data.insert(4, '# Geom=Checkpoint Guess=Read\n')
            # Creating folder and writing the input files
            error_input_folder = (self.input_folder + '/{}'.format(error))
            if not os.path.exists(error_input_folder):
                os.mkdir(error_input_folder)
            error_input_file = error_input_folder + '/{}.gjf'.format(name)
            with open(error_input_file, 'w') as input_file:
                input_file.writelines(input_data)
        print(
            'Finished.\n'
            'Total time:{}'.format(datetime.now() - start)
        )

    def files_distribution(self, path, number):
        """
        Distributed files into sub folders that can be applied for array jobs on
        barkla.

        :param path: The root folder
        :param number: The number of files in each sub-folders
        :type path: str
        :type number: int
        :return: None
        """
        print('Starting...')
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
        print('Finished!\n'
              'Distributed into {} folders.'.format((i - 1)))

    def files_redistribution(self, path):
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

    def obtain_structure(self):
        """
        Obtain the final structure for  geometry optimisation result. The
        formation energy is written in the second line as atom unit and saved
        as an XYZ format file.

        :return: None
        """
        print('Start...')
        start = datetime.now()
        for out_file in os.listdir(self.normal_result_folder):
            # Parameters initialisation
            result_ending, result_starting = 0, 0
            find_hf, final_result, coordinate_lines = False, '', []
            out_file_path = self.normal_result_folder + '/' + out_file
            with open(out_file_path, 'r') as file:
                lines = file.readlines()
            # Finding the starting and ending point for final result
            for j in range(len(lines)-1, -1, -1):
                if ('State=' in lines[j]) or ('Version=' in lines[j]):
                    result_ending = j + 1
                    find_hf = True
                elif find_hf and lines[j].startswith(' 1\\1\\'):
                    result_starting = j
                    break
            for i in range(result_starting, result_ending+1):
                final_result += lines[i][1:-1]
            result_list = final_result.split('\\\\')
            energy = re.search('HF=-?[0-9]+.[0-9]+', result_list[4]).group(0)
            for coordinate in result_list[3].split('\\')[1:]:
                segments = coordinate.split(',')
                coordinate_line = '{}{:>20}{:>20}{:>20}\n'.format(
                    # Element and coordinates
                    segments[0],
                    segments[1],
                    segments[2],
                    segments[3]
                )
                coordinate_lines.append(coordinate_line)
            # xyz format lines list
            name = out_file.split('.')[0]
            xyz_title_lines = ['{}\n'.format(len(coordinate_lines)),
                               '{} Energy: {} A.U.\n'.format(name, energy)]
            xyz_format_lines = xyz_title_lines + coordinate_lines
            path = self.mol_result + '/{}.xyz'.format(name)
            with open(path, 'w') as mol_file:
                mol_file.writelines(xyz_format_lines)
        print(
            'Finished.\n'
            'XYZ format files in:  {}\n'
            'Total time:{}'.format(self.mol_result, (datetime.now() - start))
        )


if __name__ == '__main__':
    gauss_function = GaussianIO(method='PM7_IP_EA', mol='dyes', seq='tetramer')
    gauss_function.info('all')
    gauss_function.obtain_structure()
