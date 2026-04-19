重构了文件结构，

1. llm_test_project_allinone：之前lh开发的测试工具，使用静态测试

2. 测试代码：推荐采用的测试代码库，proxy.py，来自 https://github.com/abhinavsingh/proxy.py
   也可以找新的测试仓库

3. test1-url，选取上面仓库中的proxy.py/proxy/http/url.py来完成的白盒测试

   url.py：测试的代码

   prompt.txt：最开始的prompt，已经把url.py复制进去

   answer.json：丢给AI生成的测试用例

   test_url.py：根据answer.json生成的测试评估脚本

   ~~~bash
   pytest test_url.py --cov=. --cov-branch --cov-report=html
   ~~~

   展示测试指标：命令执行后，你的目录下会生成一个 htmlcov 文件夹。打开里面的 index.html。