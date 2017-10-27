# -*- coding: utf-8 -*-
import json
import os
import threading
import argparse
from tools import simctl
from classes.device_type import DeviceType
from classes.runtime import RunTime
import socket
from contextlib import closing
import subprocess
from classes.daemon import Daemon
import time

TEMP_FOLDER = "/tmp/"
NODE_CONFIG_FILE_NAME = "node_config.json"

class AppiumDaemon(Daemon):
    def run(self):
        process = subprocess.Popen(self.appium)
        self.rewrite_pid(process.pid)
        process.wait()

def start (name: str, device_type: DeviceType , runtime: RunTime,
           threads: int, hub_host: str, hub_port: int, host: str, delay: int):
    device_type = DeviceType(identifier=device_type)
    runtime = RunTime(identifier=runtime)
    for i in range(threads):
        device = simctl.SimCtl.create_device(name+str(i), device_type, runtime)
        print("Create simulator with uuid " + device.uuid)
        port = get_free_port()
        generate_node_config_file(device_type, runtime, hub_host, hub_port, port, host)
        appium = ["appium","-p",str(port),
                  "-dc",get_default_capabilities(device.uuid),
                  "--nodeconfig", os.path.abspath(NODE_CONFIG_FILE_NAME)]
        print("Appium server started for port "+str(port))
        thread_appium = threading.Thread(target=run_appium_server, args=([TEMP_FOLDER+name+str(i), appium]))
        thread_appium.start()
        time.sleep(delay)

def stop(name):
    devices = simctl.SimCtl.get_devices_by_prefix(name)
    for i, device in enumerate(devices):
        device.delete()
        proc = AppiumDaemon(TEMP_FOLDER+name+str(i),None)
        proc.stop()


def get_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('localhost', 0))
        return s.getsockname()[1]

def run_appium_server(pid, appium):
    proc = AppiumDaemon(pid, appium)
    proc.start()


def get_default_capabilities(udid):
    return json.dumps({"udid": udid, "wdaLocalPort" : get_free_port()})

def generate_node_config_file(device_type, runtime, hub_host, hub_port, port, host):
    node_config_json = json.dumps({
          "capabilities": [
            {
              "deviceName": device_type.identifier,
              "version": runtime.identifier,
              "maxInstances": 1,
              "platformName": "iOS",
              "platform": "mac",
              "browserName": "safari"
            }
          ],
          "configuration": {
            "cleanUpCycle": 2000,
            "timeout": 30000,
            "proxy": "org.openqa.grid.selenium.proxy.DefaultRemoteProxy",
            "url": "http://"+str(host)+":"+str(port)+"/wd/hub",
            "host": host,
            "port": port,
            "maxSession": 1,
            "browserTimeout": 30,
            "register": True,
            "registerCycle": 5000,
            "hubPort": hub_port,
            "hubHost": hub_host
          }
        })
    if os.path.exists(NODE_CONFIG_FILE_NAME): os.remove(NODE_CONFIG_FILE_NAME)
    with open(NODE_CONFIG_FILE_NAME, 'w') as file:
        file.write(node_config_json)

def parse_options():

    parser = argparse.ArgumentParser()

    parser.add_argument("-m", "--method", help="Stop or Start script", dest="method")
    parser.add_argument("-n", "--name", help="Base name for instances", dest="name")
    parser.add_argument("-d", "--device_type", help="Device type of simulator", dest="device_type")
    parser.add_argument("-r", "--runtime", help="Runtime type of simulator", dest="runtime")
    parser.add_argument("-t", "--threads", help="Number of threads for tests", dest="threads")
    parser.add_argument("--host", help="Host of the instance", dest="host")
    parser.add_argument("--hub_host", help="Host of the selenium grid", dest="hub_host")
    parser.add_argument("--hub_port", help="Port of the selenium grid", dest="hub_port")
    parser.add_argument("--delay", help="Simulators creation delay", dest="delay")

    args = parser.parse_args()
    if args.method == "start":
        start(args.name, args.device_type, args.runtime, int(args.threads),
              args.hub_host, args.hub_port, args.host, int(args.delay))
    else:
        stop(args.name)


if __name__ == "__main__":
    parse_options()
