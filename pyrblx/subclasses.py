import xxhash
import zstandard as zstd

class PropertyDescriptor():
    def __init__(self, memory, address, parent):
        self.memory = memory
        self.address = address
        self.parent = parent
    
    def __bool__(self):
        return self.address > 0
    
    def get_name(self):
        try:
            offset = 0x8
            ptr = self.memory.readptr(self.address + offset)

            return self.memory.readstring2(ptr)
        except Exception as e:
            return ""
    
    def get_type(self):
        try:
            offset = 0x0 # Dunno the offset
            ptr = self.memory.readptr(self.address + offset)

            return self.memory.readstring2(ptr)
        except Exception as e:
            return ""
    
    def get_value(self):
        try:
            offset = 0x0 # Dunno the offset
            addr = self.memory.readptr(self.address + offset)

            return addr
        except Exception as e:
            return ""

class BoundFunction():
    def __init__(self, memory, address, parent):
        self.memory = memory
        self.address = address
        self.parent = parent
    
    def __bool__(self):
        return self.address > 0
    
    def get_name(self):
        try:
            offset = 0x8
            ptr = self.memory.readptr(self.address + offset)

            return self.memory.readstring2(ptr)
        except Exception as e:
            return ""
    
    def get_function(self):
        try:
            offset = 0x70 # not sure
            return self.memory.readptr(self.address + offset)
        except Exception as e:
            return 0
    
    def get_security(self):
        try:
            offset = 0x4C # not sure
            return self.memory.readint(self.address + offset)
        except Exception as e:
            return 0
        
    def execute(self, *args, timeout=5000):
        parent_addr = self.parent.address
        func_addr = self.get_function()

        code_size = 0x200
        code_addr = self.memory.allocate(code_size)

        ret_offset = 0xF8
        ret_addr = code_addr + ret_offset

        code = bytearray()

        # Implement execution

        ok = self.memory.writebytes(code_addr, bytes(code))

        finished = self.memory.thread(code_addr, timeout=timeout)
        result = self.memory.readptr(ret_addr)

        self.memory.process.free(code_addr)

        return result

class EventDescriptor():
    def __init__(self, memory, address, parent):
        self.memory = memory
        self.address = address
        self.parent = parent
    
    def __bool__(self):
        return self.address > 0
    
    def get_name(self):
        try:
            offset = 0x8
            ptr = self.memory.readptr(self.address + offset)

            return self.memory.readstring2(ptr)
        except Exception as e:
            return ""

class ScriptBytecode():
    def __init__(self):
        self.k_magic = b"RSB1"
        self.k_mult = 41
        self.k_seed = 42
    
    def encode(self, raw: bytes):
        cctx = zstd.ZstdCompressor()
        compressed = cctx.compress(raw)

        ss = bytearray(4 + 4 + len(compressed))
        ss[0:4] = b"\x00\x00\x00\x00"
        ss[4:8] = len(raw).to_bytes(4, "little")
        ss[8:] = compressed

        rehash = xxhash.xxh32(ss, seed=self.k_seed).intdigest()
        hb = bytearray(rehash.to_bytes(4, "little"))

        for i in range(len(ss)):
            ss[i] ^= (hb[i % 4] + i * self.k_mult) & 0xFF

        for i in range(4):
            hb[i] = (hb[i] + i * self.k_mult) & 0xFF
            hb[i] ^= self.k_magic[i]

        ss[0:4] = hb

        return bytes(ss)

    def decode(self, content):
        ss = bytearray(content)

        if len(ss) < 8:
            return b""
        
        hb = bytearray(ss[:4])
        for i in range(4):
            hb[i] ^= self.k_magic[i]
            hb[i] = (hb[i] - i * self.k_mult) & 0xFF

        for i in range(len(ss)):
            ss[i] ^= (hb[i % 4] + i * self.k_mult) & 0xFF

        expected_hash = int.from_bytes(hb, "little", signed=False)
        rehash = xxhash.xxh32(ss, seed=self.k_seed).intdigest()

        if rehash != expected_hash:
            return b""
        
        decompressed_size = int.from_bytes(ss[4:8], "little", signed=False)
        
        dctx = zstd.ZstdDecompressor()
        try:
            decompressed = dctx.decompress(ss[8:], max_output_size=decompressed_size)
            return decompressed
        except Exception as e:
            return b""