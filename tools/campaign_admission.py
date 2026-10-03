"""Local two-phase submission control. Callers must hold the named mutex.

This is coordination between the authorized collector/probe, not an auth boundary.
"""
import json
import contextlib
import ctypes as ct
from pathlib import Path
import time


def transition(path: Path,action: str) -> dict:
    data=json.loads(path.read_text(encoding='utf-8'))
    state=data['state']
    if action=='permit' and state=='ready':data['state']='permitted'
    elif action=='submit' and state=='permitted':data['state']='submitted'
    elif action=='ready' and state=='prepared':data['state']='ready'
    elif action=='abort':
        data['abort_requested']=True
        if state not in ('submitted','drained'):data['state']='aborted'
    elif action=='drained' and state=='submitted':data['state']='drained'
    else:raise ValueError(f'Invalid admission transition {state}/{action}')
    if action in ('permit','submit') and data.get('abort_requested'):raise ValueError('Submission revoked')
    path.write_text(json.dumps(data)+'\n',encoding='utf-8')
    return data


class Admission:
    """Mutex serializes permit/revoke against actual overlapped submission."""
    def __init__(self,path: Path,name: str,*,create: bool=False):
        self.path=path;self.name=name;self.k=ct.WinDLL('kernel32',use_last_error=True)
        self.k.CreateMutexW.argtypes=[ct.c_void_p,ct.c_int,ct.c_wchar_p];self.k.CreateMutexW.restype=ct.c_void_p
        self.k.OpenMutexW.argtypes=[ct.c_uint32,ct.c_int,ct.c_wchar_p];self.k.OpenMutexW.restype=ct.c_void_p
        self.k.WaitForSingleObject.argtypes=[ct.c_void_p,ct.c_uint32];self.k.WaitForSingleObject.restype=ct.c_uint32
        self.k.ReleaseMutex.argtypes=[ct.c_void_p];self.k.ReleaseMutex.restype=ct.c_int
        self.k.CloseHandle.argtypes=[ct.c_void_p];self.k.CloseHandle.restype=ct.c_int
        self.handle=self.k.CreateMutexW(None,False,name) if create else self.k.OpenMutexW(0x00100001,False,name)
        if not self.handle:raise ct.WinError(ct.get_last_error())

    @contextlib.contextmanager
    def locked(self):
        status=self.k.WaitForSingleObject(self.handle,2000)
        if status==0x80:
            self.k.ReleaseMutex(self.handle);raise RuntimeError('Abandoned admission mutex')
        if status!=0:raise RuntimeError('Admission mutex deadline')
        try:yield
        finally:
            if not self.k.ReleaseMutex(self.handle):raise ct.WinError(ct.get_last_error())

    def wait_permission(self):
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            with self.locked():
                data=json.loads(self.path.read_text(encoding='utf-8'))
                if data.get('abort_requested') or data['state']=='aborted':raise RuntimeError('Submission revoked')
                if data['state']=='permitted':return
                if data['state']!='ready':raise RuntimeError('Invalid readiness state')
            time.sleep(0.02)
        raise RuntimeError('Controller permission deadline; no request submitted')

    def close(self):
        if self.handle:
            self.k.CloseHandle(self.handle);self.handle=None
