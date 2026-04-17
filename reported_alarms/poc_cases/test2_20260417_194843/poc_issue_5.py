import os
f = open('test_leak.txt', 'w')
f.write('data')
# File not closed, resource leak
print(os.path.exists('test_leak.txt'))
