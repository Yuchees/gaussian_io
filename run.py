from gaussian_io import read_out

output_test = read_out('./gaussian_io/test/output_std.out')
output_test.parser_optimisation()
a = output_test.get_opt_step(step=1)
print('')
