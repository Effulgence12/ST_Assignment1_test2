from pathlib import Path
backup_root = './reports'
report_name = '../../etc/passwd'
report_path = Path(backup_root) / report_name
print(report_path.resolve())  # Resolves outside intended directory
