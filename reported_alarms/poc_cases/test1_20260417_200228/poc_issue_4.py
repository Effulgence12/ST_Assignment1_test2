try:
    raise KeyboardInterrupt()
except:
    pass
# Bare except catches KeyboardInterrupt, preventing graceful exit
