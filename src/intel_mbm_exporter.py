#!/usr/bin/env python3

import argparse
import os
import signal
import sys
import time
from typing import Dict

import prometheus_client
from utils import read_env, read_sys_info, run_proc


g_processes = {}


class IntelMbmMetrics:
    """
    Fetch and transform metrics into Prometheus format
    """

    def __init__(self, interval=1):
        self.interval = interval
        # hardware system info
        self.sys_info = read_sys_info()
        # Prometheus metrics
        self.mem_bw = prometheus_client.Gauge(
            "cpu_mem_bw",
            "CPU memory bandwidth in MB/s",
            labelnames=["cpu", "mem_node"]
        )
        self.mem_node_variants = ["local", "remote", "all"]


    def start_pqos(self):
        pqos_root = os.path.join(read_env()["ROOT"], "tools/intel-cmt-cat")
        env = {
            "LD_LIBRARY_PATH": os.path.join(pqos_root, "lib"),
        }
        mon_list = ",".join(f"[{x}]" for x in self.sys_info["cpu_list"].values())
        mon_term = ""
        for metric in ["llc", "mbt", "mbl", "mbr"]:
            mon_term += f"{metric}:{mon_list};"
        cmd = [
            os.path.join(pqos_root, "pqos/pqos"),
            "-r",
            "--disable-mon-ipc", "--disable-mon-llc_miss",
            "-i", str(10 * self.interval),
            "-m", f"{mon_term.rstrip(';')}"
        ]
        g_processes["pqos"] = run_proc(cmd, env=env, get_proc=True, for_real=True)


    def run_metrics_loop(self):
        self.start_pqos()
        proc = g_processes.get("pqos", None)
        while proc:
            line = proc.stdout.readline().decode("utf-8")
            if line == "":
                if proc.poll() is not None:
                    break
                else:
                    time.sleep(max(int(self.interval/10), 1))
            # print(line.strip(), flush=True)
            items = line.strip().split()
            for node_idx, cpu_list in self.sys_info["cpu_list"].items():
                if cpu_list.startswith(items[0]):
                    for idx, mem_node in enumerate(self.mem_node_variants):
                        self.mem_bw.labels(node_idx, mem_node).set(float(items[2 + idx]))


def handler(signum, frame):
     print("Cleanup underlying processes ...", flush=True)
     for name, proc in g_processes.items():
         print(f"\tKilling {name}", flush=True)
         proc.terminate()
     print("Exiting ...")
     sys.exit(1)


def main(args):
    # config prometheus client
    prometheus_client.REGISTRY.unregister(prometheus_client.PLATFORM_COLLECTOR)
    prometheus_client.REGISTRY.unregister(prometheus_client.GC_COLLECTOR)
    # start http server
    prometheus_client.start_http_server(args.port)
    # setup metrics
    mbm_metrics = IntelMbmMetrics(args.interval)
    mbm_metrics.run_metrics_loop()


def init_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--interval", "-i", type=int, default=15, help="interval in seconds")
    parser.add_argument("--port", "-p", type=int, default=9798, help="exporter port")
    return parser


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
    parser = init_parser()
    args = parser.parse_args()
    if os.getuid() != 0:
        print("Error: Intel pqos tool requires root permission")
        sys.exit(1)
    main(args)

