
# python 3.7 >= is required!

import os
import io
import threading
import queue

import connection
from type import Uint8, Uint16, OpaqueUint16, OpaqueLength
from disp import hexdump

from protocol_tlscontext import TLSContext
from protocol_types import ContentType, HandshakeType
from protocol_recordlayer import TLSPlaintext, TLSCiphertext, TLSInnerPlaintext
from protocol_handshake import Handshake
from protocol_hello import ClientHello
from protocol_ciphersuite import CipherSuites, CipherSuite
from protocol_extensions import Extensions, Extension, ExtensionType
from protocol_ext_version import SupportedVersions, \
    ProtocolVersions, ProtocolVersion
from protocol_ext_supportedgroups import NamedGroupList, NamedGroups, NamedGroup
from protocol_ext_signature import SignatureSchemeList, \
    SignatureSchemes, SignatureScheme
from protocol_ext_keyshare import KeyShareHello, \
    KeyShareEntrys, KeyShareEntry, OpaqueUint16
from protocol_authentication import Finished, Hash, OpaqueHash

from crypto_x25519 import x25519
import crypto_hkdf as hkdf

messages = bytearray(0)
tls_messages = {}

dhkex_class = x25519

secret_key = os.urandom(32)
public_key = dhkex_class(secret_key)

client_hello = TLSPlaintext(
    type=ContentType.handshake,
    fragment=Handshake(
        msg_type=HandshakeType.client_hello,
        msg=ClientHello(
            cipher_suites=CipherSuites([
                CipherSuite.TLS_CHACHA20_POLY1305_SHA256,
                CipherSuite.TLS_EMPTY_RENEGOTIATION_INFO_SCSV
            ]),
            extensions=Extensions([
                Extension(
                    extension_type=ExtensionType.supported_versions,
                    extension_data=SupportedVersions(
                        versions=ProtocolVersions([
                            ProtocolVersion.TLS13
                        ])
                    )
                ),
                Extension(
                    extension_type=ExtensionType.supported_groups,
                    extension_data=NamedGroupList(
                        named_group_list=NamedGroups([
                            NamedGroup.x25519
                        ])
                    )
                ),
                Extension(
                    extension_type=ExtensionType.signature_algorithms,
                    extension_data=SignatureSchemeList(
                        supported_signature_algorithms=SignatureSchemes([
                            SignatureScheme.rsa_pss_rsae_sha256,
                            SignatureScheme.rsa_pss_rsae_sha384,
                            SignatureScheme.rsa_pss_rsae_sha512,
                        ])
                    )
                ),
                Extension(
                    extension_type=ExtensionType.key_share,
                    extension_data=KeyShareHello(
                        shares=KeyShareEntrys([
                            KeyShareEntry(
                                group=NamedGroup.x25519,
                                key_exchange=OpaqueUint16(public_key)
                            )
                        ])
                    )
                )
            ])
        )
    )
)
tls_messages['ClientHello'] = client_hello
messages += bytes(client_hello.fragment)

print(client_hello)
print('[>>>] Send:')
print(hexdump(bytes(client_hello)))

client_conn = connection.ClientConnection('localhost', 50007)
# client_conn = connection.ClientConnection('enabled.tls13.com', 443)
client_conn.send_msg(bytes(client_hello))

buf = None
while not buf:
    buf = client_conn.recv_msg()
print('[<<<] Recv:')
print(hexdump(buf))

stream = io.BytesIO(buf)

# Server Hello
server_hello = TLSPlaintext.from_fs(stream)
print(server_hello)
tls_messages['ServerHello'] = server_hello
messages += bytes(server_hello.fragment)

ctx = TLSContext()
ctx.set_key_exchange(client_hello, server_hello, dhkex_class, secret_key)
Hash.length = ctx.hash_size

print('[+] shared key:', ctx.shared_key.hex())

# Key Schedule
ctx.key_schedule_in_handshake(messages)

# TODO: 現在のstreamに加えて、他にデータが送られていないか確認した後に、以下のループに入ること
# Finished を受信したことを確認してから以下のループを抜けること

is_recv_serverhello = False # TODO: ServerHelloを受け取る処理も以下のループでできるように
is_recv_finished = False

while True:
    # buf = None
    # while not buf:
    #     buf = client_conn.recv_msg()
    #
    # stream = io.BytesIO(buf)

    while True:
        firstbyte = stream.read(1)
        if firstbyte == b'':
            continue
        stream.seek(-1, io.SEEK_CUR)

        content_type = ContentType(Uint8(int.from_bytes(firstbyte, byteorder='big')))

        if content_type == ContentType.change_cipher_spec:
            # ChangeCipherSpec
            change_cipher_spec = TLSPlaintext.from_fs(stream)
            print(change_cipher_spec)
            # tls_messages['ChangeCipherSpec'] = change_cipher_spec

        elif content_type in (ContentType.handshake, ContentType.application_data):
            # EncryptedExtensions, Certificate, CertificateVerify, Finished

            obj = TLSCiphertext.from_fs(stream).decrypt(ctx.server_traffic_crypto)
            print(obj)
            tls_messages[obj.fragment.msg.__class__.__name__] = obj
            messages += bytes(obj.fragment)

            if obj.fragment.msg.__class__.__name__ == 'Finished':
                print('[*] Received Finished!')
                is_recv_finished = True
                break

    if is_recv_finished:
        break

# Finished
finished_key = hkdf.HKDF_expand_label(
    ctx.client_hs_traffic_secret, b'finished', b'', ctx.hash_size, ctx.hash_name)
verify_data = hkdf.secure_HMAC(
    finished_key, hkdf.transcript_hash(messages, ctx.hash_name), ctx.hash_name)
finished = TLSPlaintext(
    type=ContentType.handshake,
    fragment=Handshake(
        msg_type=HandshakeType.finished,
        msg=Finished(
            verify_data=OpaqueHash(bytes(verify_data))
        )
    )
)
print(finished)
print(hexdump(bytes(finished)))

tlsciphertext = finished.encrypt(ctx.client_traffic_crypto)
print(tlsciphertext)
print(hexdump(bytes(tlsciphertext)))

client_conn.send_msg(bytes(tlsciphertext))

# Key Schedule
ctx.key_schedule_in_app_data(messages)

loop_keyboard_input = True

def read_keyboard_input(inputQueue):
    print('Ready for keyboard input:')
    while loop_keyboard_input:
        input_str = input()
        inputQueue.put(input_str + "\n")

inputQueue = queue.Queue()
inputThread = threading.Thread(target=read_keyboard_input,
                               args=(inputQueue,), daemon=True)
inputThread.start()

print("=== Application Data ===")
try:
    while True:

        buf = None
        while not buf:
            buf = client_conn.recv_msg()

            # 受信待機時にクライアント側から入力があれば送信する
            if inputQueue.qsize() > 0:
                input_str = inputQueue.get()
                app_data = TLSPlaintext(
                    type=ContentType.application_data,
                    fragment=OpaqueLength(input_str.encode())
                )
                print(hexdump(bytes(app_data)))

                tlsciphertext = app_data.encrypt(ctx.client_app_data_crypto)
                print(tlsciphertext)
                print('[>>>] Send:')
                print(hexdump(bytes(tlsciphertext)))

                client_conn.send_msg(bytes(tlsciphertext))

        print('[<<<] Recv:')
        print(hexdump(buf))

        stream = io.BytesIO(buf)

        while True:
            firstbyte = stream.read(1)
            if firstbyte == b'':
                break
            stream.seek(-1, io.SEEK_CUR)

            obj = TLSCiphertext.from_fs(stream) \
                .decrypt(ctx.server_app_data_crypto)
            print(obj)

            if isinstance(obj.fragment, Handshake):
                # New Session Ticket
                print('[+] New Session Ticket arrived!')
                tls_messages[obj.fragment.msg.__class__.__name__] = obj

            else:
                print(bytes(obj.fragment))

except KeyboardInterrupt:
    print('\nBye!')

loop_keyboard_input = False

client_conn.close()

# memo:
#
# openssl_server
#   ~/local/bin/openssl s_server -accept 50007 \
#     -cert ./cert/server.crt -key ./cert/server.key -tls1_3 -state -debug
# openssl_make
#   cd ~/local/download/openssl-OpenSSL_1_1_1c/build
#   make -j4 && make install_runtime install_dev
# client
#   python client.py
