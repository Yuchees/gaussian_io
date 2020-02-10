# gaussian_io
This is a Python library that provides for reading and editing [Gaussian 16](http://gaussian.com/gaussian16/) input and output files.   
It also provides error detection and 3D coordinates exportation.

## Functions
 * *read_out:* Read *.out* file
 * *read_in:*  Read and edit *.gjf* file
 * *write_xyz:* Generate an XYZ format file from object coord attributes.
 * *write_in:* Write mult-GaussianIn objects as links in a .gjf file.

## Objects
 * *GaussianOut:* Class for parsing an output file
 * *GaussianIn:* Class for parsing an input file
 
## Author
 * Yu Che
