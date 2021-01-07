import unittest
from os import path
from fragview.encryption import EncryptedFile, generate_key, decrypt, CryptoErr
from tests.utils import TempDirMixin


class TestDecrypt(unittest.TestCase, TempDirMixin):
    """
    test decrypt() function
    """

    FILE = "crypt-tst"
    DATA = b"for a second time, the Tummal fell into ruin"

    def setUp(self):
        self.setup_temp_dir()
        self.filepath = path.join(self.temp_dir, self.FILE)
        self.enc_key = generate_key()

    def tearDown(self):
        self.tear_down_temp_dir()

    def _write_encrypted(self):
        with EncryptedFile(self.enc_key, self.filepath) as f:
            f.write(self.DATA)

    def test_ok(self):
        """
        test the happy path, when we successfully decrypt a valid file
        """
        self._write_encrypted()

        plaintext = decrypt(self.enc_key, self.filepath)
        self.assertEqual(plaintext, self.DATA)

    def test_wrong_key(self):
        """
        test the case when wrong encryption key is used
        """
        self._write_encrypted()

        # create a new different encryption key
        new_key = bytearray(self.enc_key)
        new_key[0] += 1

        with self.assertRaisesRegex(CryptoErr, "MAC check failed"):
            decrypt(new_key, self.filepath)

    def test_too_short(self):
        """
        test the case when encrypted files is to short, i.e. corrupted
        """
        with open(self.filepath, "wb") as f:
            # write 10 bytes long file
            f.write(self.DATA[:10])

        with self.assertRaisesRegex(CryptoErr, "file too short"):
            decrypt(self.enc_key, self.filepath)

    def test_mac_error(self):
        """
        test the case when encrypted files is corrupted
        """
        with open(self.filepath, "wb") as f:
            f.write(self.DATA)

        with self.assertRaisesRegex(CryptoErr, "MAC check failed"):
            decrypt(self.enc_key, self.filepath)
