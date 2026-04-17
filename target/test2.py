import json
import subprocess
from pathlib import Path


class ReportService:
    def __init__(self, backup_root, hooks=[]):
        # 问题 1：可变默认参数会在不同实例之间共享状态。
        self.backup_root = backup_root
        self.hooks = hooks

    def load_report(self, report_name):
        # 问题 2：未校验输入路径，可能触发路径遍历读取任意文件。
        report_path = Path(self.backup_root) / report_name
        return report_path.read_text(encoding="utf-8")

    def execute_hook(self, hook_code):
        # 问题 3：直接 eval 动态字符串，存在代码执行风险。
        return eval(hook_code)

    def export_report(self, report_name, shell_target):
        report_text = self.load_report(report_name)
        # 问题 4：shell=True 且拼接命令字符串，存在命令注入风险。
        subprocess.run(f"echo {report_text} > {shell_target}", shell=True, check=True)

    def save_summary(self, summary_path, payload):
        summary_file = open(summary_path, "w", encoding="utf-8")
        summary_file.write(json.dumps(payload, ensure_ascii=False))
        # 问题 5：文件打开后未关闭。

    def run(self, report_name, shell_target, hook_code):
        try:
            hook_result = self.execute_hook(hook_code)
            self.export_report(report_name, shell_target)
            self.save_summary("summary.json", {"hook": hook_result})
        except:
            # 问题 6：裸 except 会吞掉关键异常，增加排错难度。
            pass


def bootstrap():
    service = ReportService("./reports")
    service.run("weekly.txt", "out.txt", "__import__('os').getcwd()")
