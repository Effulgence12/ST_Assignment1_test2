try:
    raise KeyboardInterrupt('User interrupted')
except:
    pass
# KeyboardInterrupt is silently swallowed, preventing graceful exit
