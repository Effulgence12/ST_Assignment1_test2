def process_data(filename, data):
    # Issue 1 - 资源管理泄漏（文件打开后未关闭）
    f = open(filename, 'w')
    f.write(data)

    # Issue 2 - 未定义变量 / 拼写错误（应为 print）
    Print("Data written successfully")

    # Issue 3 - 安全漏洞（动态执行不可信代码）
    exec("print('Executing dynamic code')")

    # Issue 4 - 潜在运行时错误 + 不推荐的裸 except
    try:
        result = 10 / 0
    except:
        pass

    return True
