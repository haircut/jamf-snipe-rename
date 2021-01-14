#!/path/to/python3
'''
Usage: 
    python3 set_computer_name_non_jamf.py <Snipe Bearer token>

# MIT License
#
# Copyright (c) 2021 Matthew Warren <bmwarren@unca.edu>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
'''

import sys
import json
import requests
import subprocess


SNIPE_SERVER = "https://your.snipe.instance"  # No trailing slash
TOKEN_SALT = ""
TOKEN_PASSPHRASE = ""


def get_hostname_from_snipe(serial, token):
    """Returns the hostname for the device in Snipe"""
    q = f"{SNIPE_SERVER}/v1/hardware/byserial/{serial}"
    auth = f"Bearer {token}"
    response = requests.get(
        q, headers={"Accept": "application/json", "Authorization": auth}
    )
    if response.status_code == 200:
        data = json.loads(response.text)
        if data["total"] > 0:
            # Snipe returns all known records of a device when doing a 'byserial'
            # lookup. The server returns this list sorted ascending, so the last
            # array element is the newest – and thus most current – record
            return data["rows"][-1]["name"]
        else:
            return False
    else:
        print(f"Snipe returned status code {response.status_code}")
        return False


def get_serial():
    """Returns this device's serial"""
    return (
        subprocess.Popen(
            "system_profiler SPHardwareDataType |grep -v tray |awk '/Serial/ {print $4}'",
            shell=True,
            stdout=subprocess.PIPE,
        )
        .communicate()[0]
        .strip()
        .decode("UTF-8")
    )


def rename_computer(n):
    """Renames the machine via scutil"""
    cmds = [
        ["/usr/sbin/scutil", "--set", "ComputerName", n],
        ["/usr/sbin/scutil", "--set", "LocalHostName", n],
        ["/usr/sbin/scutil", "--set", "HostName", n]
    ]
    results = {
        "success": True
    }
    for cmd in cmds:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        if not proc.returncode == 0:
            results["success"] = False
            break
    return results


def decrypt_token(input_token):
    """
    Reference: https://github.com/jamf/Encrypted-Script-Parameters/blob/master/EncryptedStrings_Python.py
    """
    proc = subprocess.Popen(
        [
            "/usr/bin/openssl",
            "enc",
            "-aes256",
            "-d",
            "-a",
            "-A",
            "-S",
            TOKEN_SALT,
            "-k",
            TOKEN_PASSPHRASE,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    return proc.communicate(input_token)[0].strip().decode("UTF-8")


def main():
    """Main"""
    # Ensure an auth token was passed as parameter 4 from Jamf
    try:
        token = decrypt_token(sys.argv[1])
    except Exception:
        print("You must provide an API token to access Snipe!")
        exit()
    serial = get_serial()
    host = get_hostname_from_snipe(serial, token)
    if host:
        print(f"Renaming to {host}")
        new_name = host
    else:
        print("Serial not found in Snipe!")
        print(f"Renaming to serial number {serial}")
        new_name = serial
    rename = rename_computer(new_name)
    if rename["success"]:
        print(f"Successfully set computer name to {new_name}")
        exit(0)
    else:
        print("Unable to set computer name.")
        exit(1)


if __name__ == "__main__":
    main()
