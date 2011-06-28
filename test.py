import os, sys, subprocess

# TODO: use os.walk
total = 0
good = 0
bad = []
mode = 'gcc' if len(sys.argv) >= 1 and sys.argv[1] == 'gcc' else 'cast'
for file in os.listdir('/usr/include'):
  if file[-2:] == '.h':
    sys.stdout.write('%s ... ' % (file))
    total += 1
    try:
      if mode == 'gcc':
        subprocess.check_call(['gcc', '-E', '/usr/include/' + file], stdout=open('/dev/null', 'w'))
      else:
        subprocess.check_call(['python3', 'c.py', '/usr/include/' + file])
      good += 1
      sys.stdout.write('OKAY\n')
    except subprocess.CalledProcessError:
      bad.append(file)
      sys.stdout.write('FAIL\n')

for b in bad:
  print('FAIL:', b)

print('\n\n%d/%d (%d%%)' % (good, total, (good/total)*100))