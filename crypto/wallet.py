# crypto/wallet.py (COMPLETE REWRITE - NO INDENTATION ERRORS)
"""
Full crypto wallet with ECDSA signing for transactions
"""

import json
import hashlib
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from crypto.secp256k1_backend import (
    CRYPTO_AVAILABLE as ECDSA_AVAILABLE,
    generate_keypair as _generate_secp_keypair,
    sign,
    verify,
    verify_batch_sha256,
)
from crypto.keys import KeyGenerator
from crypto import native

# Wallet file format: encrypted keystore v1 (scrypt + AES-256-GCM) or explicit plaintext.
_WALLET_KEYSTORE_VERSION = 1
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32


@dataclass
class KeyPair:
    private_key: bytes
    public_key: bytes
    address: str


class Wallet:
    """Cryptocurrency wallet with ECDSA signing"""
    
    def __init__(self, keypair: KeyPair = None):
        self.keypair = keypair or self._generate_keypair()
    
    def _generate_keypair(self) -> KeyPair:
        """Generate new secp256k1 keypair"""
        if not ECDSA_AVAILABLE:
            raise RuntimeError("SECP256K1 backend not available")
        private_key, public_key = _generate_secp_keypair()
        
        address = self._derive_address(public_key)
        
        return KeyPair(
            private_key=private_key,
            public_key=public_key,
            address=address
        )
    
    def _derive_address(self, public_key: bytes) -> str:
        """Derive chain address from public key (delegates to KeyGenerator)."""
        from crypto.keys import KeyGenerator

        return KeyGenerator.derive_address(public_key)
    
    @property
    def address(self) -> str:
        return self.keypair.address
    
    @property
    def public_key(self) -> str:
        return self.keypair.public_key.hex()
    
    @property
    def private_key(self) -> str:
        return self.keypair.private_key.hex()
    
    def sign_transaction(
        self,
        to: str,
        value: int,
        nonce: int,
        chain_id: int = 1,
        data: str = "",
        gas_limit: int = 21000,
        *,
        amount_satoshi: int | None = None,
    ) -> dict:
        """Create and sign a transaction (optional calldata + gas for EVM deploy/call).

        ``amount_satoshi`` is dual-write metadata (not in ECDSA digest); when set
        it must match ``to_satoshi(value)`` (ADR 0021 mismatch refuse).
        """
        from runtime.amount import to_satoshi

        if amount_satoshi is not None:
            amt_sat = int(amount_satoshi)
            if amt_sat < 0:
                raise ValueError("value_negative")
            if int(to_satoshi(value)) != amt_sat:
                raise ValueError("value_satoshi_mismatch")
        else:
            amt_sat = int(to_satoshi(value))
        tx = {
            "from": self.address,
            "to": to,
            "value": value,
            "amount_satoshi": amt_sat,
            "nonce": nonce,
            "chain_id": chain_id,
            "gas_limit": int(gas_limit),
            "data": data or "",
        }

        tx_hash = self._hash_transaction(tx)
        signature = self._sign_hash(tx_hash)

        tx["signature"] = signature
        tx["public_key"] = self.public_key
        tx["hash"] = tx_hash

        return tx

    @staticmethod
    def _canonical_tx_for_hash(tx: dict) -> dict:
        """Canonical signing payload; includes data/gas only when non-default."""
        payload = {
            "from": tx["from"],
            "to": tx["to"],
            "value": tx["value"],
            "nonce": tx["nonce"],
            "chain_id": tx.get("chain_id", 1),
        }
        data = tx.get("data", "") or ""
        if data:
            payload["data"] = data
        gas_limit = tx.get("gas_limit") or tx.get("gas")
        if gas_limit is not None and int(gas_limit) != 21000:
            payload["gas_limit"] = int(gas_limit)
        return payload

    def _hash_transaction(self, tx: dict) -> str:
        """Create canonical hash of transaction for signing."""
        encoded = json.dumps(
            self._canonical_tx_for_hash(tx),
            sort_keys=True,
            separators=(",", ":"),
        )
        return native.hash_sorted_json(encoded)

    def _sign_hash(self, data_hash: str) -> str:
        """Sign a hash with private key"""
        if not ECDSA_AVAILABLE:
            raise RuntimeError("SECP256K1 backend not available")
        
        signature = sign(data_hash.encode(), self.keypair.private_key, hashfunc=hashlib.sha256)
        return signature.hex()
    
    def sign_block(self, block: dict) -> str:
        """Sign a block as proposer"""
        block_hash = self._hash_block(block)
        return self._sign_hash(block_hash)
    
    def _hash_block(self, block: dict) -> str:
        block_for_hash = {
            "number": block.get("number"),
            "parent_hash": block.get("parent_hash"),
            "timestamp": block.get("timestamp"),
            "proposer": block.get("proposer")
        }
        # Legacy contract: default json.dumps separators (spaces), sort_keys=True.
        encoded = json.dumps(block_for_hash, sort_keys=True)
        return native.sha256_hex(encoded.encode())
    
    def sign_attestation(self, attestation: dict) -> str:
        """Sign an attestation as validator"""
        att_hash = self._hash_attestation(attestation)
        return self._sign_hash(att_hash)
    
    def _hash_attestation(self, attestation: dict) -> str:
        """Hash attestation for signing"""
        att_for_hash = {
            "validator": attestation.get("validator"),
            "target_hash": attestation.get("target_hash"),
            "target_height": attestation.get("target_height"),
            "slot": attestation.get("slot")
        }
        encoded = json.dumps(att_for_hash, sort_keys=True, separators=(',', ':'))
        return native.hash_sorted_json(encoded)
    
    @staticmethod
    def _scrypt_derive(password: str, salt: bytes) -> bytes:
        from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

        return Scrypt(
            salt=salt,
            length=_SCRYPT_DKLEN,
            n=_SCRYPT_N,
            r=_SCRYPT_R,
            p=_SCRYPT_P,
        ).derive(password.encode("utf-8"))

    def _encrypted_keystore_blob(self, password: str) -> dict:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        if not password or not str(password).strip():
            raise ValueError("password required for encrypted wallet export")
        salt = os.urandom(16)
        nonce = os.urandom(12)
        key = self._scrypt_derive(str(password), salt)
        ciphertext = AESGCM(key).encrypt(nonce, self.keypair.private_key, None)
        return {
            "version": _WALLET_KEYSTORE_VERSION,
            "address": self.address,
            "public_key": self.public_key,
            "crypto": {
                "cipher": "aes-256-gcm",
                "ciphertext": ciphertext.hex(),
                "nonce": nonce.hex(),
                "kdf": "scrypt",
                "kdfparams": {
                    "n": _SCRYPT_N,
                    "r": _SCRYPT_R,
                    "p": _SCRYPT_P,
                    "dklen": _SCRYPT_DKLEN,
                    "salt": salt.hex(),
                },
            },
        }

    @staticmethod
    def _atomic_write_json(filepath: str, data: dict) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    def export(
        self,
        filepath: str,
        password: str = None,
        *,
        allow_plaintext: bool = False,
    ):
        """Export wallet to file.

        - ``password`` set → scrypt + AES-256-GCM keystore (never plaintext).
        - ``password`` omitted → plaintext JSON (legacy/dev). Prefer password.
          ``allow_plaintext=True`` is accepted for explicit callers; omitted
          password alone still writes plaintext for backward compatibility.
        """
        if password is not None:
            self._atomic_write_json(filepath, self._encrypted_keystore_blob(password))
            return
        # Legacy plaintext path (ops smoke / older labs). Password is never ignored:
        # a non-None password always takes the encrypted branch above.
        _ = allow_plaintext  # explicit opt-in documented for new callers
        self._atomic_write_json(
            filepath,
            {
                "version": 0,
                "plaintext": True,
                "address": self.address,
                "public_key": self.public_key,
                "private_key": self.private_key,
            },
        )

    @classmethod
    def _wallet_from_private(cls, private_key: bytes, *, address: str = "", public_key_hex: str = "") -> "Wallet":
        public_key = KeyGenerator.private_to_public(private_key)
        derived = KeyGenerator.derive_address(public_key)
        if address and str(address).strip().lower() != derived.lower():
            raise ValueError("wallet import refused: address does not match private key")
        if public_key_hex:
            try:
                stated = bytes.fromhex(str(public_key_hex).replace("0x", ""))
            except (TypeError, ValueError) as exc:
                raise ValueError("wallet import refused: malformed public_key") from exc
            if stated != public_key:
                raise ValueError("wallet import refused: public_key does not match private key")
        return cls(
            KeyPair(
                private_key=private_key,
                public_key=public_key,
                address=derived,
            )
        )

    @classmethod
    def import_wallet(
        cls,
        filepath: str,
        password: str = None,
        *,
        allow_plaintext: bool = False,
    ) -> "Wallet":
        """Import wallet from encrypted keystore or legacy plaintext file.

        Password is never ignored: encrypted files require it; plaintext files
        refuse a non-None password (call without password for legacy JSON).
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        crypto = data.get("crypto")
        if isinstance(crypto, dict):
            if password is None or not str(password).strip():
                raise ValueError("password required to import encrypted wallet")
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

            params = crypto.get("kdfparams") or {}
            try:
                salt = bytes.fromhex(str(params["salt"]))
                nonce = bytes.fromhex(str(crypto["nonce"]))
                ciphertext = bytes.fromhex(str(crypto["ciphertext"]))
                n = int(params.get("n", _SCRYPT_N))
                r = int(params.get("r", _SCRYPT_R))
                p = int(params.get("p", _SCRYPT_P))
                dklen = int(params.get("dklen", _SCRYPT_DKLEN))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("wallet import refused: malformed keystore") from exc
            if str(crypto.get("cipher") or "").lower() != "aes-256-gcm":
                raise ValueError("wallet import refused: unsupported cipher")
            if str(crypto.get("kdf") or "").lower() != "scrypt":
                raise ValueError("wallet import refused: unsupported kdf")
            key = Scrypt(salt=salt, length=dklen, n=n, r=r, p=p).derive(
                str(password).encode("utf-8")
            )
            try:
                private_key = AESGCM(key).decrypt(nonce, ciphertext, None)
            except Exception as exc:
                raise ValueError("wallet import refused: bad password or corrupt keystore") from exc
            return cls._wallet_from_private(
                private_key,
                address=str(data.get("address") or ""),
                public_key_hex=str(data.get("public_key") or ""),
            )

        if "private_key" not in data:
            raise ValueError("wallet import refused: no private_key or crypto blob")
        if password is not None:
            raise ValueError(
                "password provided but file is plaintext JSON; "
                "refuse to ignore password — use encrypted export or omit password"
            )
        _ = allow_plaintext
        try:
            private_key = bytes.fromhex(str(data["private_key"]).replace("0x", ""))
        except (TypeError, ValueError) as exc:
            raise ValueError("wallet import refused: malformed private_key") from exc
        return cls._wallet_from_private(
            private_key,
            address=str(data.get("address") or ""),
            public_key_hex=str(data.get("public_key") or ""),
        )
    
    @classmethod
    def create_new(cls) -> "Wallet":
        return cls()
    
    @classmethod
    def from_private_key(cls, private_key_hex: str) -> "Wallet":
        private_key = bytes.fromhex(private_key_hex)
        public_key = KeyGenerator.private_to_public(private_key)
        address = KeyGenerator.derive_address(public_key)
        keypair = KeyPair(
            private_key=private_key,
            public_key=public_key,
            address=address
        )
        return cls(keypair)
    
    @classmethod
    def _derive_address(cls, public_key: bytes) -> str:
        return "0x" + native.sha256_hex(public_key)[-40:]


# ========== SIGNATURE VERIFICATION ==========

def verify_transaction_signature(tx: dict) -> bool:
    """Verify transaction signature.

    Wave Q: missing ECDSA backend is unavailable (RuntimeError), not invalid False.
    Check availability before material so sender-bind failures do not mask
    ``unavailable``.
    """
    if not ECDSA_AVAILABLE:
        raise RuntimeError("signature verify unavailable: ECDSA backend missing")
    material = _transaction_signature_material(tx)
    if material is None:
        return False
    message, signature, public_key = material
    return verify(message, signature, public_key, hashfunc=hashlib.sha256)


def verify_transaction_signatures_batch(txs: List[dict]) -> List[bool]:
    """Batch verify canonical transaction signatures."""
    if not ECDSA_AVAILABLE:
        raise RuntimeError("signature verify unavailable: ECDSA backend missing")

    batch: List[Tuple[bytes, bytes, bytes]] = []
    positions: List[int] = []
    results = [False for _ in txs]

    for idx, tx in enumerate(txs):
        material = _transaction_signature_material(tx)
        if material is None:
            continue
        batch.append(material)
        positions.append(idx)

    if not batch:
        return results

    verified = verify_batch_sha256(batch)
    for idx, ok in zip(positions, verified):
        results[idx] = bool(ok)

    return results


def _transaction_signature_material(tx: dict) -> Optional[Tuple[bytes, bytes, bytes]]:
    """Build ECDSA verify material with mandatory sender↔pubkey binding.

    Signature must verify under ``public_key``, and ``derive_address(public_key)``
    must equal ``tx["from"]``. Without that binding, an attacker could set
    ``from`` to a victim address while signing with their own key.
    """
    if "signature" not in tx or "public_key" not in tx:
        return None
    sender = str(tx.get("from") or "").strip()
    if not sender:
        return None

    try:
        signature = bytes.fromhex(str(tx["signature"]))
        public_key = bytes.fromhex(str(tx["public_key"]))
    except (TypeError, ValueError):
        return None

    try:
        derived = KeyGenerator.derive_address(public_key)
    except (TypeError, ValueError, AttributeError):
        return None
    if str(derived).strip().lower() != sender.lower():
        return None

    tx_to_verify = Wallet._canonical_tx_for_hash({
        "from": sender,
        "to": tx["to"],
        "value": tx["value"],
        "nonce": tx["nonce"],
        "chain_id": tx.get("chain_id", 1),
        "data": tx.get("data", ""),
        "gas_limit": tx.get("gas_limit") or tx.get("gas"),
    })

    tx_hash_hashed = native.hash_sorted_json(
        json.dumps(tx_to_verify, sort_keys=True, separators=(",", ":"))
    )

    return tx_hash_hashed.encode(), signature, public_key


def create_test_wallet() -> Wallet:
    return Wallet.create_new()
