from Cryptodome import Random
from Cryptodome.Cipher import AES

# encryption key size, in bytes
KEY_SIZE = 16

# access token size
TOKEN_SIZE = 32


class EncryptedFile:
    def __init__(self, key, file_path):
        self.key = key
        self.file_path = file_path

    def __enter__(self):
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
