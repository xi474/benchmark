"""Invoke the existing focused check entry point, including def-main-only legacy checks."""
import os,runpy,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve();folder=sys.argv[2];path=root/folder
sys.path.insert(0,str(root));sys.path.insert(0,str(path));os.chdir(path)
namespace=runpy.run_module(folder.replace('/','.')+'.check_module',run_name='__reward_v2_focused__')
if callable(namespace.get('main')):namespace['main']()
