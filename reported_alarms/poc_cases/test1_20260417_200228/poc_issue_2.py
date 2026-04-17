import os
f = open('test_leak.txt', 'w')
f.write('data')
# File is never closed, leading to potential resource leak
print(os.path.exists('test_leak.txt'))
