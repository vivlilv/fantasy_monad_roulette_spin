"""
hardcoded values:
proxy in init BidManager class
bidder_handle in create_bid function


exception logic
create bid - no server response handling
insufficient balance(MON,fMON)
Not an owner of tokenId

utility helpers
input the accounts for bidder and acceptor
fetch nfts for accounts
"""

# Hardcoded values removal
import json
import time
import random
from web3 import Web3
import requests
from capmonster_python import TurnstileTask
from datetime import datetime, timezone, timedelta
from eth_account.messages import encode_defunct
import requests
from typing import Optional, Dict


# basic config
def connect_rpc():
    w3 = Web3(Web3.HTTPProvider("https://testnet-rpc.monad.xyz/"))
    print("Connection status to Monad:", w3.is_connected())
    return w3




# privy id token retrival class
class GetToken:
    def __init__(self, private_key, wallet_address):
        self.session = requests.Session()
        self.web3 = connect_rpc()
        self.private_key = private_key
        self.wallet_address = wallet_address

    def get_auth_token(self, captcha_token="4e4805e767d5c7f97b73863b98aeea17"):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": "https://monad.fantasy.top",
            "Referer": "https://monad.fantasy.top/",
            "privy-app-id": "cm6ezzy660297zgdk7t3glcz5",
            "privy-client": "react-auth:1.92.3",
            "privy-client-id": "client-WY5gEtuoV4UpG2Le3n5pt6QQD61Ztx62VDwtDCZeQc3sN",
            "privy-ca-id": "bdbb1f47-e59a-4f0d-b6b4-1c00fc2d36e6",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        }

        # Step 1: Get fresh captcha
        captcha_token = self._get_captcha_token()
        if not captcha_token:
            raise Exception("Captcha solving failed")

        print(f"[Captcha Token] {captcha_token}")

        # Step 2: Get nonce
        init_response = self.session.post(
            "https://auth.privy.io/api/v1/siwe/init",
            json={"address": self.wallet_address, "token": captcha_token},
            headers=headers,
            timeout=10,
        )

        print(f"[Init Response] {init_response.status_code} - {init_response.text}")
        if init_response.status_code != 200:
            raise Exception(
                f"Init failed ({init_response.status_code}): {init_response.text}"
            )

        nonce = init_response.json()["nonce"]

        # Step 3: Create message
        message = self._create_sign_message(self.wallet_address, nonce)
        print(f"[SIWE Message]\n{message}")

        signed_message = self._sign_message(message, self.private_key)
        print(f"[Signature] {signed_message.signature.hex()}")

        # Step 4: Authenticate
        auth_response = self.session.post(
            "https://auth.privy.io/api/v1/siwe/authenticate",
            json={
                "chainId": "eip155:1",
                "message": message,
                "signature": "0x" + signed_message.signature.hex(),
                "walletClientType": "metamask",
                "mode": "login-or-sign-up",
            },
            headers=headers,
            timeout=10,
        )

        print(f"[Auth Response] {auth_response.status_code} - {auth_response.text}")
        if auth_response.status_code != 200:
            raise Exception(
                f"Auth failed ({auth_response.status_code}): {auth_response.text}"
            )

        privy_token = auth_response.json()["token"]

        # Step 5: Final App Token
        final_response = self.session.post(
            "https://monad.fantasy.top/api/auth/privy",
            json={"address": self.wallet_address},
            headers={**headers, "Authorization": f"Bearer {privy_token}"},
            timeout=10,
        )

        print(f"[Final Response] {final_response.status_code} - {final_response.text}")
        if final_response.status_code != 200:
            raise Exception(
                f"Final token failed ({final_response.status_code}): {final_response.text}"
            )

        return auth_response.json()["identity_token"]

    def _get_captcha_token(self):
        try:
            capmonster = TurnstileTask("4e4805e767d5c7f97b73863b98aeea17")
            task_id = capmonster.create_task(
                website_url="https://monad.fantasy.top",
                website_key="0x4AAAAAAAM8ceq5KhP1uJBt",
            )
            result = capmonster.join_task_result(task_id)
            token = result.get("token")
            if token:
                print(token)
                return token
        except Exception as e:
            print(f"Error getting captcha token: {e}")
        return None

    def _create_sign_message(self, wallet_address, nonce):
        lines = []
        lines.append(
            f"monad.fantasy.top wants you to sign in with your Ethereum account:"
        )
        lines.append(f"{wallet_address}")
        lines.append("")
        lines.append(
            f"By signing, you are proving you own this wallet and logging in. This does not initiate a transaction or cost any fees."
        )
        lines.append("")
        lines.append(f"URI: https://monad.fantasy.top")
        lines.append(f"Version: 1")
        lines.append(f"Chain ID: 10143")  # Ensure this is correct for the testnet
        lines.append(f"Nonce: {nonce}")
        lines.append(
            f"Issued At: {datetime.utcnow().isoformat(timespec='milliseconds')}Z"
        )  # Ensure correct timestamp format
        lines.append(f"Resources:")
        lines.append(f"- https://privy.io")

        return "\n".join(lines)

    def _sign_message(self, message, private_key):
        # Sign the message using the private key
        signed_message = self.web3.eth.account.sign_message(
            encode_defunct(message.encode("utf-8")), private_key
        )
        return signed_message
