import os

import pymem
import pymem.process
from pymem.ressources.kernel32 import VirtualProtectEx
from pymem.ressources.structure import MEMORY_BASIC_INFORMATION

import ctypes
from ctypes import wintypes
import struct
import psutil
import re
import json
import requests

from classes import *

PAGE_EXECUTE_READWRITE = 0x40
PAGE_READWRITE = 0x04
MEM_COMMIT = 0x1000

class Memory():
    def __init__(self, app):
        self.app = app
        self.struct = struct

        self.target = "RobloxPlayerBeta.exe"

        self.process = None
        self.base = None
        self.scheduler = None

        self.object_pool = {}

        self.offsets = {}

        self.load_offsets()

    def download_offsets(self, target):
        data = requests.get("https://raw.githubusercontent.com/NtReadVirtualMemory/Roblox-Offsets-Website/main/offsets.json")

        if data and data.status_code == 200 and data.content:
            with open(target, 'w') as file:
                json.dump(data.json(), file, indent=1)

    def load_offsets_default(self):
        self.offsets.setdefault("ClassDescriptorToPropertyDescriptor", "0x9C0")
        self.offsets.setdefault("ClassDescriptorToEventDescriptor", "0xa68")
        self.offsets.setdefault("ClassDescriptorToBoundFunction", "0xb10")
    
    def load_offsets(self, offsetsfile=None):
        path = None

        if offsetsfile != None:
            path = offsetsfile
        else:
            path = os.path.join(self.app.path, 'offsets.json')
            self.download_offsets(path)

        with open(path, 'r') as file:
            self.offsets = json.load(file)

        self.load_offsets_default()
    
    def process_find(self, name=None):
        if name is None:
            name = self.target
        
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] == name:
                return proc.info['pid']

        return None
    
    def process_find_path(self, name=None):
        if name is None:
            name = self.target
        
        for proc in psutil.process_iter(['name', 'exe']):
            if proc.info['name'] == name:
                return proc.info['exe']

        return None

    def process_attach(self, name=None):
        if name is None:
            name = self.target
        
        try:
            self.process = pymem.Pymem(name)
            module = pymem.process.module_from_name(self.process.process_handle, name)
            self.base = module.lpBaseOfDll

            self.scheduler = Scheduler(self)

            return True
        except Exception:
            return False
    
    def process_is_open(self):
        return self.process is not None and self.process.process_handle is not None
    
    def pack_u64(self, v):
        return int(v).to_bytes(8, 'little', signed=False)

    def pack_u32(self, v):
        return int(v).to_bytes(4, 'little', signed=False)
    
    def protect(self, address, size=4, prot=PAGE_EXECUTE_READWRITE):
        old_protect = ctypes.c_ulong()
        success = VirtualProtectEx(
            self.process.process_handle,
            ctypes.c_void_p(address),
            size,
            prot,
            ctypes.byref(old_protect)
        )

        return bool(success)
    
    def allocate(self, size):
        try:
            addr = self.process.allocate(size)
        except Exception:
            addr = 0

        if not addr:
            return 0
        
        self.protect(addr, size)

        return addr
    
    def free(self, address):
        self.process.free(address)
    
    def thread(self, start_address, timeout=5000):
        kernel32 = ctypes.windll.kernel32

        thread_handle = kernel32.CreateRemoteThread(
            ctypes.c_void_p(self.process.process_handle),
            None,
            0,
            ctypes.c_void_p(start_address),
            None,
            0,
            None
        )
        if not thread_handle:
            return 0

        WAIT_OBJECT_0 = 0x00000000
        INFINITE = 0xFFFFFFFF
        res = kernel32.WaitForSingleObject(thread_handle, timeout)

        kernel32.CloseHandle(thread_handle)

        return res == WAIT_OBJECT_0
    
    def scan(self, pattern, multiple=False):
        return pymem.pattern.pattern_scan_all(
            self.process.process_handle,
            pattern,
            return_multiple=multiple
        )

    def get_offset(self, name):
        string = self.offsets.get(name, "0x0")
        return int(string, 16)

    def get_datamodel(self):
        if not self.base or not self.scheduler:
            return 0

        return self.scheduler.get_datamodel()

    def get_visualengine(self):
        if not self.base or not self.scheduler:
            return 0

        return self.scheduler.get_visualengine()
    
    def get_instance(self, base, address):
        if address in self.object_pool:
            return self.object_pool[address]

        anyinst = base(self, address)

        classtype = anyinst.get_class()
        if classtype in CLASSTYPES:
            anyinst = CLASSTYPES[classtype](self, address)

        self.object_pool[address] = anyinst
        
        return anyinst
    
    def readptr(self, address):
        try:
            return self.process.read_longlong(address)
        except Exception as e:
            return 0
    
    def writeptr(self, address, value):
        self.protect(address, 8)

        try:
            self.process.write_longlong(address, value)
            return True
        except Exception as e:
            return False

    def readint(self, address):
        try:
            return self.process.read_int(address)
        except Exception as e:
            return 0

    def writeint(self, address, value):
        self.protect(address, 4)

        try:
            self.process.write_int(address, value)
            return True
        except Exception as e:
            return False
    
    def readdouble(self, address):
        try:
            return self.process.read_double(address)
        except Exception as e:
            return 0.0

    def writedouble(self, address, value):
        self.protect(address, 8)

        try:
            self.process.write_double(address, value)
            return True
        except Exception as e:
            return False

    def readfloat(self, address):
        try:
            return self.process.read_float(address)
        except Exception as e:
            return 0.0

    def writefloat(self, address, value):
        self.protect(address, 4)

        try:
            self.process.write_float(address, value)
            return True
        except Exception as e:
            return False
    
    def readfloats(self, address, amount):
        try:
            floatbytes = self.readbytes(address, amount * 4)
            floats = []

            for i in range(amount):
                start = i * 4
                part = floatbytes[start:start + 4]

                if len(part) == 4:
                    floats.append(struct.unpack('f', part)[0])
                else:
                    floats.append(0.0)
            
            return floats
        except Exception as e:
            return [0.0] * amount
    
    def writefloats(self, address, values):
        self.protect(address, len(values) * 4)

        try:
            floatbytes = b''.join(struct.pack('f', v) for v in values)

            self.writebytes(address, floatbytes)

            return True
        except Exception as e:
            return False
    
    def readnumber(self, address):
        return self.readptr(address)
    
    def writenumber(self, address, value):
        return self.writeptr(address, value)
    
    def readbool(self, address):
        try:
            return self.process.read_bool(address)
        except Exception as e:
            return False
    
    def writebool(self, address, value):
        self.protect(address, 1)

        try:
            self.process.write_bool(address, value)
            return True
        except Exception as e:
            return False
    
    def readboolmask(self, address, mask):
        try:
            byte = self.readbytes(address, 1)
            return (byte & mask) != 0
        except Exception as e:
            return False
    
    def writeboolmask(self, address, mask, value):
        self.protect(address, 1)
        
        try:
            byte = self.readbytes(address, 1)

            if value:
                byte |= mask
            else:
                byte &= ~mask

            return self.writebytes(address, byte)
        except Exception as e:
            return False

    def readbytes(self, address, size):
        try:
            return self.process.read_bytes(address, size)
        except Exception as e:
            return b'\x00' * size
    
    def writebytes(self, address, value):
        self.protect(address, len(value))

        try:
            self.process.write_bytes(address, value, len(value))
            return True
        except Exception as e:
            return False
    
    def readstring(self, address):
        if not address:
            return ""
        
        string = ""
        offset = 0

        while True:
            try:
                char = self.process.read_bytes(address + offset, 1)[0]
                if char == 0:
                    break
                
                string += chr(char)
            except:
                break
            offset += 1

        return string

    def readstring2(self, addr):
        if not addr:
            return ""
        try:
            length = self.readint(addr + 0x18)

            if length >= 16:
                newaddr = self.readptr(addr)
                return self.readstring(newaddr)
            else:
                return self.readstring(addr)
        except Exception as e:
            return ""
    
    def writestring(self, address, value):
        if not address:
            return False
        try:
            b = value.encode('utf-8') + b'\x00'
            return self.writebytes(address, b)
        except Exception:
            return False

    def writestring2(self, addr, value):
        if not addr:
            return False
        try:
            b = value.encode('utf-8')
            length = len(b)

            self.protect(addr, length)

            if not self.writeint(addr + 0x18, length):
                return False

            if length < 16:
                return self.writestring(addr, value)
            else:
                ptr = self.readptr(addr)
                if not ptr:
                    try:
                        alloc_addr = self.process.allocate(length + 1)
                    except Exception:
                        alloc_addr = 0

                    if not alloc_addr:
                        return self.writestring(addr, value) and self.writeptr(addr, addr)

                    ok = self.writestring(alloc_addr, value)
                    if not ok:
                        try:
                            try:
                                self.process.free(alloc_addr)
                            except Exception:
                                structure.free_memory(self.process.process_handle, alloc_addr)
                        except Exception:
                            pass
                        return False

                    return self.writeptr(addr, alloc_addr)
                else:
                    return self.writestring(ptr, value)
        except Exception as e:
            return False
    
    def readlist(self, address, filter):
        data = []

        try:
            start = self.readptr(address)
            end = self.readptr(address + 0x8)

            i = start
            while i < end:
                addr = self.readptr(i)
                if addr:
                    data.append(filter(addr))
                i += 0x8
        except Exception as e:
            pass

        return data

    def writelist(self, address, data):
        if not address:
            return False
        try:
            start = self.readptr(address)

            i = start
            for obj in data:
                self.writeptr(i, obj.address)
                i += 0x8
            
            self.writeptr(address + 0x8, i)

            return True
        except Exception as e:
            return False
    
    def close(self):
        if self.process:
            self.process.close_process()
            self.process = None
            self.base = None
            self.scheduler = None