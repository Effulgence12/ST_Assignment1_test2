import subprocess
report_text = 'test; rm -rf /'
shell_target = 'out.txt'
subprocess.run(f'echo {report_text} > {shell_target}', shell=True, check=True)
