
from type import Uint8, Uint16, Opaque, List
import structmeta as meta

from protocol_extensions import Extension, Extensions

# ------------------------------------------------------------------------------
# Key Exchange Layer

ProtocolVersion = Uint16
Random = Opaque(32)
OpaqueUint8 = Opaque(size_t=Uint8)
CipherSuite = Uint16
CipherSuites = List(size_t=Uint16, elem_t=CipherSuite)

@meta.struct
class ClientHello(meta.StructMeta):
    legacy_version: ProtocolVersion = ProtocolVersion(0x0303)
    random: Random
    legacy_session_id: OpaqueUint8
    cipher_suites: CipherSuites
    legacy_compression_methods: OpaqueUint8
    extensions: Extensions

@meta.struct
class ServerHello(meta.StructMeta):
    legacy_version: ProtocolVersion = ProtocolVersion(0x0303)
    random: Random
    legacy_session_id_echo: OpaqueUint8
    cipher_suite: CipherSuite
    legacy_compression_methods: OpaqueUint8
    extensions: Extensions


if __name__ == '__main__':
    import unittest

    class TestUint(unittest.TestCase):

        def test_clienthello(self):

            ch = ClientHello(
                random=Random(bytes.fromhex('AA' * 32)),
                legacy_session_id=OpaqueUint8(bytes.fromhex('BB' * 32)),
                cipher_suites=CipherSuites([
                    CipherSuite(0x1302), CipherSuite(0x1303),
                    CipherSuite(0x1301), CipherSuite(0x00ff)]),
                legacy_compression_methods=OpaqueUint8(b'\x00'),
                extensions=Extensions([]),
            )

            expected = bytes.fromhex(
                '03 03 AA AA AA AA AA AA  AA AA AA AA AA AA AA AA' \
                'AA AA AA AA AA AA AA AA  AA AA AA AA AA AA AA AA' \
                'AA AA 20 BB BB BB BB BB  BB BB BB BB BB BB BB BB' \
                'BB BB BB BB BB BB BB BB  BB BB BB BB BB BB BB BB' \
                'BB BB BB 00 08 13 02 13  03 13 01 00 FF 01 00 00' \
                '00                                              ' )

            self.assertEqual(bytes(ch), expected)
            self.assertEqual(ClientHello.from_bytes(bytes(ch)), ch)

        def test_clienthello_has_extensions(self):

            from protocol_extensions import ExtensionType
            from protocol_ext_supportedgroups import NamedGroupList, NamedGroups, NamedGroup

            ch = ClientHello(
                random=Random(bytes.fromhex('AA' * 32)),
                legacy_session_id=OpaqueUint8(bytes.fromhex('BB' * 32)),
                cipher_suites=CipherSuites([
                    CipherSuite(0x1302), CipherSuite(0x1303),
                    CipherSuite(0x1301), CipherSuite(0x00ff)]),
                legacy_compression_methods=OpaqueUint8(b'\x00'),
                extensions=Extensions([
                    Extension(
                        extension_type=ExtensionType.supported_groups,
                        extension_data=NamedGroupList(
                            named_group_list=NamedGroups([
                                NamedGroup.x25519, NamedGroup.secp256r1,
                            ])
                        )
                    ),
                    Extension(
                        extension_type=ExtensionType.supported_groups,
                        extension_data=NamedGroupList(
                            named_group_list=NamedGroups([
                                NamedGroup.x25519, NamedGroup.secp256r1,
                            ])
                        )
                    ),
                ]),
            )

            self.assertEqual(ClientHello.from_bytes(bytes(ch)), ch)

    unittest.main()
