from Cryptodome import Random

# encryption key size, in bytes
KEY_SIZE = 16


def generate_key():
    """
    generate a new random encryption key, suitable
    for AES encryption we are using
    """
    # and write it to the specified key file
    return Random.get_random_bytes(KEY_SIZE)
