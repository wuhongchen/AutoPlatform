import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)
from core.manager import AutoPlatformManager

mgr = AutoPlatformManager()
url = "https://mp.weixin.qq.com/s/nc54LfE5hMiUWHwEHR6piA" # This is a sample URL
mgr.run_with_params(url)
