import sys

with open(sys.argv[1], 'r') as f:
    lines = f.readlines()

with open(sys.argv[1], 'w') as f:
    for line in lines:
        if line.startswith('pick 743a7d3'):
            f.write(line.replace('pick', 'edit', 1))
        else:
            f.write(line)
