"""Author-only real Linux PTY implementation, not a command-output simulator."""
import errno,os,pty,select,signal,tempfile,time
from pathlib import Path


KEYS={'Enter':b'\r','C-c':b'\x03','C-d':b'\x04','C-u':b'\x15','Tab':b'\t','Backspace':b'\x7f'}


def transform(payload):
    chunks=[];closed=False
    with tempfile.TemporaryDirectory(prefix='pty-task-') as folder:
        home=Path(folder);rc=home/'bashrc'
        (home/'.hushlogin').touch()
        rc.write_text("PS1='PROMPT> '\nPS2='CONT> '\nHISTFILE=/dev/null\n"+payload.get('startup','')+'\n',encoding='utf-8')
        pid,master=pty.fork()
        if pid==0:
            os.chdir(folder)
            env=dict(os.environ,HOME=folder,TERM='dumb',LC_ALL='C',HISTFILE='/dev/null')
            os.execve('/bin/bash',['bash','--noprofile','--rcfile',str(rc),'-i'],env)
        def read_until(marker):
            nonlocal closed
            data=b'';deadline=time.monotonic()+payload.get('timeout_seconds',4)
            target=None if marker is None else marker.encode()
            while time.monotonic()<deadline:
                ready,_,_=select.select([master],[],[],max(0,deadline-time.monotonic()))
                if not ready:break
                try:b=os.read(master,65536)
                except OSError as e:
                    if e.errno!=errno.EIO:raise
                    b=b''
                if not b:
                    closed=True;break
                data+=b
                if target is not None and target in data.replace(b'\r\n',b'\n').replace(b'\r',b''):
                    # Drain bytes already produced in the same terminal output burst.
                    while select.select([master],[],[],0.01)[0]:
                        try:more=os.read(master,65536)
                        except OSError:more=b''
                        if not more:closed=True;break
                        data+=more
                    break
            if target is not None and target not in data.replace(b'\r\n',b'\n').replace(b'\r',b''):raise RuntimeError('public terminal marker not reached')
            if target is None and not closed:raise RuntimeError('terminal did not exit')
            return data.decode('utf-8').replace('\r\n','\n').replace('\r','')
        try:
            chunks.append(read_until('PROMPT> '))
            for step in payload['steps']:
                data=b''.join(KEYS[k] if k in KEYS else k.encode() for k in step['keys'])
                os.write(master,data)
                chunks.append(read_until(step['until']))
        finally:
            try:os.killpg(pid,signal.SIGHUP)
            except ProcessLookupError:pass
            os.close(master)
            try:os.waitpid(pid,0)
            except ChildProcessError:pass
    return dict(chunks=chunks,closed=closed)

from pathlib import Path
import json
def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def build_component(input_path,output_path):
    value=transform(load_payload(input_path))
    p=Path(output_path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    return value
