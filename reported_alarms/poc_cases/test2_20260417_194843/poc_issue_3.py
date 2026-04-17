hook_code = "__import__('os').system('echo pwned')"
result = eval(hook_code)
print(result)
