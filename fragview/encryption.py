from os import path
from Cryptodome import Random
from Cryptodome.Cipher import AES

# encryption key size, in bytes
KEY_SIZE = 16

# access token size
TOKEN_SIZE = 32


class CryptoErr(Exception):
    def error_message(self):
        return self.args[0]


class EncryptedFile:
    def __init__(self, key, file_path):
        self.key = key
        self.file_path = file_path

    def __enter__(self):
        # use 16-byte nonce, as recommended for the EAX mode
        nonce = Random.get_random_bytes(16)
        self.cipher = AES.new(self.key, AES.MODE_EAX, nonce)
        self.file = open(self.file_path, "wb")

        # write down 'nonce' in the beginning of the file
        self.file.write(nonce)

        return self

    def write(self, data):
        self.file.write(self.cipher.encrypt(data))

    def __exit__(self, exc_type, exc_val, exc_tb):
        # TODO: handle exception thrown (e.g. exc_type et al are set)
        self.file.write(self.cipher.digest())
        self.file.close()


def generate_token():
    return Random.get_random_bytes(TOKEN_SIZE)


def generate_key():
    """
    generate a new random encryption key, suitable
    for AES encryption we are using
    """
    # and write it to the specified key file
    return Random.get_random_bytes(KEY_SIZE)


# src_file - django uploaded file
def encrypt(key, src_file, dest_file):
    with EncryptedFile(key, dest_file) as dest:
        # encrypt uploaded file by chunks
        for chunk in src_file.chunks():
            dest.write(chunk)


def decrypt(key, src_file):
    src_size = path.getsize(src_file)

    # encrypted files must be atleas 32 bytes
    # fist 16 bytes are nonce, last 16 bytes are MAC tag
    if src_size < 32:
        raise CryptoErr("file to short")

    with open(src_file, "rb") as src:
        nonce = src.read(16)
        cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
        ciphertext = src.read(src_size - 32)

        # decrypt
        plaintext = cipher.decrypt(ciphertext)

        # load MAC tag and verify integrity of the file
        mac_tag = src.read()
        try:
            cipher.verify(mac_tag)
        except ValueError as e:
            # MAC check failed, source file corrupted
            raise CryptoErr(e.args[0])

        return plaintext
