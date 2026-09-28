import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "drone-telemetry", "src_any"))
import msgpack_lite  # noqa: E402


class MsgpackLiteTest(unittest.TestCase):
    def roundtrip(self, obj):
        self.assertEqual(msgpack_lite.unpackb(msgpack_lite.packb(obj)), obj)

    def test_scalars(self):
        for obj in (None, True, False, 0, 1, 127, 128, 255, 256, 65535, 65536,
                    2 ** 32, 2 ** 63, -1, -32, -33, -128, -129, -32768, -32769,
                    -2 ** 31 - 1, -2 ** 63, 0.0, 1.5, -123.456):
            self.roundtrip(obj)

    def test_strings_and_bin(self):
        for s in ("", "a", "x" * 31, "x" * 32, "x" * 300, "x" * 70000, "Kyiv ✈"):
            self.roundtrip(s)
        self.roundtrip(b"\x00\x01" * 200)

    def test_containers(self):
        self.roundtrip([])
        self.roundtrip(list(range(20)))
        self.roundtrip({"k%d" % i: i for i in range(20)})
        self.roundtrip([0, 7, "getMultirotorState", ["SimpleFlight"]])
        self.roundtrip({"kinematics_estimated": {"position": {"x_val": 1.0, "y_val": -2.0, "z_val": -3.0}}})

    def test_float32_decoding(self):
        # rpclib (AirSim server) encodes C++ float as msgpack float32 (0xCA)
        self.assertAlmostEqual(msgpack_lite.unpackb(b"\xca" + struct.pack(">f", 1.25)), 1.25)

    def test_streaming_unpacker(self):
        data = msgpack_lite.packb([1, 1, None, True]) + msgpack_lite.packb({"a": [1, 2, 3]})
        unpacker = msgpack_lite.Unpacker()
        received = []
        for i in range(len(data)):          # feed one byte at a time
            unpacker.feed(data[i:i + 1])
            received.extend(unpacker)
        self.assertEqual(received, [[1, 1, None, True], {"a": [1, 2, 3]}])


if __name__ == "__main__":
    unittest.main()
