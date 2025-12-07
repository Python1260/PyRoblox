import os
import subprocess
import struct
from blake3 import blake3

KEY_BYTES = bytes([0x01, 0x02, 0x03, 0x04])
MAGIC_A = 0xAAAAAAAA
MAGIC_B = 0x55555555
FOOTER_SIZE = 40

def rotl8(value, shift):
    shift &= 7
    value &= 0xFF
    return ((value << shift) | (value >> (8 - shift))) & 0xFF

class Compiler():
    def __init__(self):
        self.execname = "Luau/luau-compile.exe"
        self.tempname = "temp.luau"

    def compile(self, luau):
        with open(self.tempname, "w") as file:
            file.write(luau)

        result = subprocess.run(
            [self.execname, "--binary", self.tempname],
            capture_output=True,
            text=False
        )
        bytecode = result.stdout

        os.remove(self.tempname)

        return result.returncode == 0, self.sign(bytecode)
    
    def sign(self, bytecode):
        if not bytecode:
            return b""
        
        blake3_hash = blake3(bytecode).digest(32)

        transformed = bytearray(32)
        for i in range(32):
            key_byte = KEY_BYTES[i & 3]
            hash_byte = blake3_hash[i]
            combined = (key_byte + i) & 0xFF

            not_key = (~key_byte) & 0xFF
            not_hash = (~hash_byte) & 0xFF

            case = i & 3
            if case == 0:
                shift = (combined & 3) + 1
                result = rotl8(hash_byte ^ not_key, shift)
            elif case == 1:
                shift = (combined & 3) + 2
                result = rotl8(key_byte ^ not_hash, shift)
            elif case == 2:
                shift = (combined & 3) + 3
                result = rotl8(hash_byte ^ not_key, shift)
            else:
                shift = (combined & 3) + 4
                result = rotl8(key_byte ^ not_hash, shift)

            transformed[i] = result

        footer = bytearray(FOOTER_SIZE)
        first_hash_dword = struct.unpack_from("<I", transformed, 0)[0]

        struct.pack_into("<I", footer, 0, first_hash_dword ^ MAGIC_B)
        struct.pack_into("<I", footer, 4, first_hash_dword ^ MAGIC_A)
        footer[8:8+32] = transformed

        signed = bytearray(bytecode) + footer
        return bytes(signed)