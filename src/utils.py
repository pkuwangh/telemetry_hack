#!/usr/bin/env python3

import os
import subprocess
from typing import Dict, List, Optional


def read_env() -> Dict[str, str]:
    # default env values
    env_vars = {}
    env_vars["ROOT"] = "/".join(os.path.abspath(__file__).split("/")[:-2])
    env_vars["HOME"] = os.getenv("HOME")
    return env_vars


def read_sys_info() -> Dict[str, str]:
    sys_info = {
        "cpu_list": {}
    }
    cmd = ["lscpu"]
    stdout = run_proc(cmd)
    for line in stdout.splitlines():
        items = line.rstrip().split()
        if line.startswith("NUMA node") and "CPU" in line:
            if len(items[1]) > 4 and items[1][4:].isdigit():
                node_idx = int(items[1][4:])
                if len(items) > 3:
                    sys_info["cpu_list"][node_idx] = items[3].replace(" ", "")
    return sys_info


def exec_cmd(
    cmd: List[str],
    for_real: bool,
    print_cmd: bool = True,
) -> None:
    cmd_str = " ".join(cmd)
    if print_cmd:
        print(cmd_str)
    if for_real:
        os.system(cmd_str)


def launch_proc(
    cmd,
    stdout,
    stderr,
    cwd=None,
    env=None,
):
    return subprocess.Popen(
        cmd,
        stdout=stdout,
        stderr=stderr,
        cwd=cwd,
        env=env,
    )


def run_proc(
    cmd: List[str],
    outfile: Optional[str]=None,
    cwd: Optional[str]=None,
    env: Dict[str, str]={},
    get_proc: bool=False,
    for_real: bool=True,
):
    env_setting = [f"{k}={v}" for k, v in env.items()]
    print(" ".join(env_setting + cmd))
    exec_env = os.environ.copy()
    if for_real:
        for k, v in env.items():
            exec_env[k] = v
        if outfile:
            with open(outfile, "wt") as fp:
                proc = launch_proc(cmd, fp, fp, cwd, exec_env)
                proc.wait()
            return None
        else:
            proc = launch_proc(cmd, subprocess.PIPE, subprocess.STDOUT, cwd, exec_env)
            if get_proc:
                return proc
            else:
                (stdout, _) = proc.communicate()
                return stdout.decode("utf-8")
    return None

