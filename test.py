import os, sys, subprocess

# TODO: use os.walk
total = 0
good = 0
bad = []
for file in os.listdir('/usr/include'):
  if file[-2:] == '.h':
    sys.stdout.write('%s ... ' % (file))
    total += 1
    try:
      subprocess.check_call(['python3', 'c.py', '/usr/include/' + file])
      good += 1
      sys.stdout.write('OKAY\n')
    except subprocess.CalledProcessError:
      bad.append(file)
      sys.stdout.write('FAIL\n')

for b in bad:
  print('FAIL:', b)

print('\n\n%d/%d (%d%%)' % (good, total, (good/total)*100))