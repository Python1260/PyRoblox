from os import remove
import subprocess

import struct
from blake3 import blake3

KEY_BYTES = bytes([0x52, 0x4F, 0x46, 0x4C])
MAGIC_A = 0x4C464F52
MAGIC_B = 0x946AC432
FOOTER_SIZE = 40

def rotl8(value, shift):
	shift &= 7
	value &= 0xFF
	return ((value << shift) | (value >> (8 - shift))) & 0xFF

class Compiler():
	def __init__(self, path="Luau/luau-compile-roblox.exe"):
		self.execname = path
		self.tempname_write = "temp_write.lua"
		self.tempname_read = "temp_read.bin"

	def get_hook(self, name, version, pid, path="Luau/hooker.lua"):
		with open(path) as file:
			content = file.read()

		return content.replace("%EXECUTOR_NAME%", name).replace("%EXECUTOR_VERSION%", str(version)).replace("%PROCESS_ID%", str(pid)) 

	def compile(self, luau):
		with open(self.tempname_write, "w") as file:
			file.write(luau)

		result = subprocess.run(
			[self.execname, self.tempname_write, self.tempname_read]
		)

		remove(self.tempname_write)
		
		if result.returncode == 0:
			with open(self.tempname_read, "rb") as file:
				bytecode = file.read()
			
			remove(self.tempname_read)
			
			return True, self.sign(bytecode)

		return False, b""
	
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