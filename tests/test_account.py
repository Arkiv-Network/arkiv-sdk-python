"""Tests for NamedAccount functionality."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from eth_account import Account
from eth_utils.exceptions import ValidationError

from arkiv.account import NamedAccount
from arkiv.exceptions import AccountNameException

from .conftest import ALICE, BOB

# Well-known test mnemonics used in these tests:
# These should NEVER be used in production - they're for testing only!
MNEMONIC_ABANDON = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
MNEMONIC_CANDY = (
    "candy maple cake sugar pudding cream honey rich smooth crumble sweet treat"
)
MNEMONIC_TEST = "test test test test test test test test test test test junk"
MNEMONIC_INVALID = "not a valid mnemonic phrase"

# Known private key and address derived from CANDY mnemonic (default path)
PRIVATE_KEY_CANDY = "0xc87509a1c067bbde78beb793e6fa76530b6382a4c0241e5e4a9ec0a0f44dc0d3"
ADDRESS_CANDY = "0x627306090abaB3A6e1400e9345bC60c78a8BEf57"


class TestNamedAccountFixtures:
    """Test NamedAccount fixtures."""

    def test_account_1_fixture(self, account_1: NamedAccount) -> None:
        """Test account_1 fixture."""
        assert isinstance(account_1, NamedAccount)
        assert account_1.name == ALICE

    def test_account_2_fixture(
        self, account_1: NamedAccount, account_2: NamedAccount
    ) -> None:
        """Test account_2 fixture."""
        assert isinstance(account_2, NamedAccount)
        assert account_2.name == BOB
        assert account_2.name != account_1.name
        assert account_2.address != account_1.address


class TestNamedAccountCreation:
    """Test NamedAccount creation methods."""

    def test_create_random_account(self) -> None:
        """Test creating a random NamedAccount."""
        name = "test-account"
        account = NamedAccount.create(name)

        assert account.name == name
        assert isinstance(account.address, str)
        assert account.address.startswith("0x")
        assert len(account.address) == 42  # Ethereum address length
        assert isinstance(account.key, bytes)
        assert len(account.key) == 32  # Private key length

    def test_from_private_key_hex_string(self) -> None:
        """Test creating NamedAccount from hex private key string."""
        name = "hex-key-account"
        private_key = PRIVATE_KEY_CANDY

        account = NamedAccount.from_private_key(name, private_key)

        assert account.name == name
        assert account.address == ADDRESS_CANDY
        assert account.key.hex() == private_key[2:]  # Without 0x prefix

    def test_from_private_key_bytes(self) -> None:
        """Test creating NamedAccount from private key bytes."""
        name = "bytes-key-account"
        private_key_bytes = bytes.fromhex(PRIVATE_KEY_CANDY[2:])  # Remove 0x prefix

        account = NamedAccount.from_private_key(name, private_key_bytes)

        assert account.name == name
        assert account.address == ADDRESS_CANDY
        assert account.key == private_key_bytes

    def test_from_mnemonic_default_params(self) -> None:
        """Test creating NamedAccount from mnemonic with default parameters."""
        name = "mnemonic-account"
        mnemonic = MNEMONIC_CANDY  # Use CANDY mnemonic to match known values

        account = NamedAccount.from_mnemonic(name, mnemonic)

        assert account.name == name
        # Known address for CANDY mnemonic with default path
        assert account.address == ADDRESS_CANDY

    def test_from_mnemonic_with_passphrase(self) -> None:
        """Test creating NamedAccount from mnemonic with passphrase."""
        name = "mnemonic-passphrase-account"
        mnemonic = MNEMONIC_CANDY
        passphrase = "test-passphrase"

        account = NamedAccount.from_mnemonic(name, mnemonic, passphrase=passphrase)

        assert account.name == name
        # Different address due to passphrase
        assert account.address != "0x9858EfFD232B4033E47d90003D41EC34EcaEda94"

    def test_from_mnemonic_custom_path(self) -> None:
        """Test creating NamedAccount from mnemonic with custom derivation path."""
        name = "mnemonic-custom-path-account"
        mnemonic = MNEMONIC_TEST
        custom_path = "m/44'/60'/0'/0/1"  # Second account

        account = NamedAccount.from_mnemonic(name, mnemonic, account_path=custom_path)

        assert account.name == name
        # Different address due to custom path
        assert account.address != "0x9858EfFD232B4033E47d90003D41EC34EcaEda94"

    def test_from_wallet_json(self) -> None:
        """Test creating NamedAccount from encrypted JSON wallet."""
        name = "wallet-account"

        # Create a test wallet
        original_account = Account.create()
        password = "test-password"
        wallet_json = json.dumps(Account.encrypt(original_account.key, password))

        # Create NamedAccount from wallet
        account = NamedAccount.from_wallet(name, wallet_json, password)

        assert account.name == name
        assert account.address == original_account.address
        assert account.key == original_account.key


class TestNamedAccountProperties:
    """Test NamedAccount properties and methods."""

    def test_basic_properties(self) -> None:
        """Test basic properties of NamedAccount."""
        name = "test-account"
        account = NamedAccount.create(name)

        # Test name property
        assert account.name == name

        # Test address property
        assert isinstance(account.address, str)
        assert account.address.startswith("0x")
        assert len(account.address) == 42

        # Test key property
        assert isinstance(account.key, bytes)
        assert len(account.key) == 32

    def test_string_representations(self) -> None:
        """Test string representations of NamedAccount."""
        name = "display-account"
        account = NamedAccount.create(name)

        # Test __repr__
        repr_str = repr(account)
        assert f"name='{name}'" in repr_str
        assert f"address='{account.address}'" in repr_str
        assert "NamedAccount" in repr_str

        # Test __str__
        str_repr = str(account)
        assert name in str_repr
        assert account.address in str_repr
        assert "(" in str_repr and ")" in str_repr

    def test_delegation_to_local_account(self) -> None:
        """Test that NamedAccount properly delegates to wrapped LocalAccount."""
        name = "delegation-account"
        account = NamedAccount.create(name)

        # Test that we can access LocalAccount methods
        assert hasattr(account, "sign_message")
        assert hasattr(account, "sign_transaction")
        assert callable(account.sign_message)
        assert callable(account.sign_transaction)

    def test_export_wallet(self) -> None:
        """Test exporting NamedAccount as encrypted JSON wallet."""
        name = "export-account"
        account = NamedAccount.create(name)
        password = "export-password"

        # Export wallet
        wallet_json = account.export_wallet(password)

        # Verify it's valid JSON
        wallet_data = json.loads(wallet_json)
        assert "address" in wallet_data
        assert "crypto" in wallet_data

        # Verify we can decrypt it back
        decrypted_key = Account.decrypt(wallet_json, password)
        assert decrypted_key == account.key


class TestNamedAccountValidation:
    """Test NamedAccount validation and error handling."""

    def test_empty_name_raises_exception(self) -> None:
        """Test that empty name raises AccountNameException."""
        local_account = Account.create()

        with pytest.raises(
            AccountNameException, match="Account name must be a non-empty string"
        ):
            NamedAccount("", local_account)

    def test_none_name_raises_exception(self) -> None:
        """Test that None name raises AccountNameException."""
        local_account = Account.create()

        with pytest.raises(
            AccountNameException, match="Account name must be a non-empty string"
        ):
            NamedAccount(None, local_account)  # type: ignore

    def test_whitespace_only_name_raises_exception(self) -> None:
        """Test that whitespace-only name raises AccountNameException."""
        local_account = Account.create()

        with pytest.raises(
            AccountNameException, match="Account name must be a non-empty string"
        ):
            NamedAccount("   ", local_account)

    def test_name_is_trimmed(self) -> None:
        """Test that account name is properly trimmed."""
        local_account = Account.create()
        name_with_spaces = "  test-account  "

        account = NamedAccount(name_with_spaces, local_account)
        assert account.name == "test-account"

    def test_invalid_private_key_raises_exception(self) -> None:
        """Test that invalid private key raises appropriate exception."""
        name = "invalid-key-account"
        invalid_key = "not-a-valid-private-key"

        with pytest.raises(ValueError):
            NamedAccount.from_private_key(name, invalid_key)

    def test_invalid_mnemonic_raises_exception(self) -> None:
        """Test that invalid mnemonic raises appropriate exception."""
        name = "invalid-mnemonic-account"
        invalid_mnemonic = MNEMONIC_INVALID

        with pytest.raises(
            ValidationError
        ):  # eth_account raises ValidationError for invalid mnemonics
            NamedAccount.from_mnemonic(name, invalid_mnemonic)

    def test_wrong_wallet_password_raises_exception(self) -> None:
        """Test that wrong wallet password raises appropriate exception."""
        name = "wrong-password-account"

        # Create a test wallet
        original_account = Account.create()
        correct_password = "correct-password"
        wrong_password = "wrong-password"
        wallet_json = json.dumps(
            Account.encrypt(original_account.key, correct_password)
        )

        with pytest.raises(ValueError):
            NamedAccount.from_wallet(name, wallet_json, wrong_password)


class TestNamedAccountEdgeCases:
    """Test edge cases and special scenarios."""

    def test_two_accounts_with_same_private_key_different_names(self) -> None:
        """Test creating two NamedAccounts with same private key but different names."""
        private_key = PRIVATE_KEY_CANDY

        account1 = NamedAccount.from_private_key("account1", private_key)
        account2 = NamedAccount.from_private_key("account2", private_key)

        assert account1.name != account2.name
        assert account1.address == account2.address
        assert account1.key == account2.key

    def test_unicode_account_names(self) -> None:
        """Test that unicode account names work properly."""
        unicode_names = ["测试账户", "🚀 rocket account", "café-account", "αβγ-account"]

        for name in unicode_names:
            account = NamedAccount.create(name)
            assert account.name == name

    def test_very_long_account_name(self) -> None:
        """Test that very long account names are handled properly."""
        long_name = "a" * 1000  # Very long name
        account = NamedAccount.create(long_name)
        assert account.name == long_name

    def test_account_name_with_special_characters(self) -> None:
        """Test account names with special characters."""
        special_names = [
            "account-with-dashes",
            "account_with_underscores",
            "account.with.dots",
            "account@email.com",
            "account#123",
            "account (with parentheses)",
        ]

        for name in special_names:
            account = NamedAccount.create(name)
            assert account.name == name


class TestNamedAccountConsistency:
    """Test consistency between different creation methods."""

    def test_same_private_key_produces_same_address(self) -> None:
        """Test that same private key always produces same address."""
        private_key = PRIVATE_KEY_CANDY
        expected_address = ADDRESS_CANDY

        # Test hex string
        account1 = NamedAccount.from_private_key("test1", private_key)
        assert account1.address == expected_address

        # Test bytes
        account2 = NamedAccount.from_private_key(
            "test2", bytes.fromhex(private_key[2:])
        )
        assert account2.address == expected_address

    def test_mnemonic_consistency(self) -> None:
        """Test that same mnemonic with same params produces same account."""
        mnemonic = MNEMONIC_CANDY
        name1, name2 = "account1", "account2"

        account1 = NamedAccount.from_mnemonic(name1, mnemonic)
        account2 = NamedAccount.from_mnemonic(name2, mnemonic)

        # Same address and key, different names
        assert account1.address == account2.address
        assert account1.key == account2.key
        assert account1.name != account2.name

    def test_roundtrip_wallet_export_import(self) -> None:
        """Test that export/import wallet is consistent."""
        original_name = "original-account"
        imported_name = "imported-account"
        password = "test-password"

        # Create original account
        original = NamedAccount.create(original_name)

        # Export and import
        wallet_json = original.export_wallet(password)
        imported = NamedAccount.from_wallet(imported_name, wallet_json, password)

        # Should have same address and key, different names
        assert imported.address == original.address
        assert imported.key == original.key
        assert imported.name == imported_name
        assert imported.name != original.name


class TestAccountMain:
    """Tests for the main() CLI function."""

    def test_main_creates_wallet_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that main creates a wallet file with correct name."""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Mock command line args
        with patch("sys.argv", ["account.py", "charlie"]):
            # Mock getpass to return a password
            with patch("getpass.getpass", return_value="test_password"):
                # Mock print to capture output
                with patch("builtins.print") as mock_print:
                    from arkiv.account import main

                    main()

        # Verify wallet file was created
        wallet_file = tmp_path / "wallet_charlie.json"
        assert wallet_file.exists()

        # Verify it's valid JSON
        with wallet_file.open() as f:
            wallet_data = json.load(f)
            assert "address" in wallet_data
            assert "crypto" in wallet_data

        # Verify output was printed
        assert mock_print.call_count >= 2

    def test_main_sanitizes_special_characters(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that special characters in name are sanitized."""
        monkeypatch.chdir(tmp_path)

        with patch("sys.argv", ["account.py", "test@account#123"]):
            with patch("getpass.getpass", return_value="password"):
                with patch("builtins.print"):
                    from arkiv.account import main

                    main()

        # Should create wallet_test_account_123.json
        wallet_file = tmp_path / "wallet_test_account_123.json"
        assert wallet_file.exists()

    def test_main_exits_if_file_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that main exits if wallet file already exists."""
        monkeypatch.chdir(tmp_path)

        # Create existing wallet file
        existing_file = tmp_path / "wallet_existing.json"
        existing_file.write_text("{}")

        with patch("sys.argv", ["account.py", "existing"]):
            with patch("builtins.print") as mock_print:
                with pytest.raises(SystemExit) as exc_info:
                    from arkiv.account import main

                    main()

        # Should exit with code 1
        assert exc_info.value.code == 1

        # Should print error message
        mock_print.assert_called_once()
        assert "already exists" in mock_print.call_args[0][0]

    def test_main_wallet_can_be_decrypted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that created wallet can be decrypted with the password."""
        monkeypatch.chdir(tmp_path)
        password = "secure_password_123"

        with patch("sys.argv", ["account.py", "decrypt_test"]):
            with patch("getpass.getpass", return_value=password):
                with patch("builtins.print"):
                    from arkiv.account import main

                    main()

        # Load and decrypt the wallet
        wallet_file = tmp_path / "wallet_decrypt_test.json"
        with wallet_file.open() as f:
            wallet_json = f.read()

        from eth_account import Account

        # Should not raise an exception
        private_key = Account.decrypt(wallet_json, password)
        assert isinstance(private_key, bytes)
        assert len(private_key) == 32

        # Verify address matches for private key with address in wallet
        account = Account.from_key(private_key)
        assert account.address.startswith("0x")
        assert len(account.address) == 42
        assert account.address == json.loads(wallet_json)["address"]
