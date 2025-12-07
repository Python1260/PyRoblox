import xxhash
import zstandard as zstd

class ScriptBytecode():
    def __init__(self):
        self.k_magic = b"RSB1"
        self.k_mult = 41
        self.k_seed = 42

    def encode(self, raw: bytes) -> bytes:
        cctx = zstd.ZstdCompressor()
        compressed = cctx.compress(raw)

        ss = bytearray(4 + 4 + len(compressed))

        ss[0:4] = self.k_magic
        ss[4:8] = len(raw).to_bytes(4, "little")
        ss[8:] = compressed

        rehash = xxhash.xxh32(bytes(ss), seed=self.k_seed).intdigest()
        hb = bytearray(rehash.to_bytes(4, "little"))

        for i in range(len(ss)):
            ss[i] ^= (hb[i % 4] + i * self.k_mult) & 0xFF

        hb_transformed = bytearray(4)
        for i in range(4):
            hb_transformed[i] = ((hb[i] + i * self.k_mult) & 0xFF) ^ self.k_magic[i]

        ss[0:4] = hb_transformed

        return bytes(ss)

    def decode(self, content: bytes) -> bytes:
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
        rehash = xxhash.xxh32(bytes(ss), seed=self.k_seed).intdigest()

        if rehash != expected_hash:
            return b""

        decompressed_size = int.from_bytes(ss[4:8], "little", signed=False)

        dctx = zstd.ZstdDecompressor()
        try:
            decompressed = dctx.decompress(bytes(ss[8:]), max_output_size=decompressed_size)
            return decompressed
        except Exception:
            return b""