import requests
import json
import os
from datetime import datetime
import time
import math
from eth_account import Account
from get_token import GetToken, connect_rpc
from web3 import Web3
from collections import defaultdict

spin_url = "https://secret-api.fantasy.top/rewards/buy-batch-fragment-roulette?batch_amount=10"

def load_accounts(input_file="privates.txt"):
    """Load accounts from file with proper error handling"""
    with open(input_file, 'r') as f:
        private_keys = [line.strip() for line in f.readlines() 
                      if line.strip() and len(line.strip()) >= 64]
    
    accounts = []
    for private_key in private_keys:
        try:
            account = Web3().eth.account.from_key(private_key)
            accounts.append({
                "address": account.address,
                "private": private_key
            })
        except Exception as e:
            print(f"Error processing key {private_key[:8]}...: {e}")
    
    if accounts:
        print(f"Loaded {len(accounts)} accounts. First address: {accounts[0]['address']}")
    else:
        print("No valid accounts loaded!")
    
    return accounts

def spin(acc):
    """Execute spin with proper error handling"""
    address = acc.get('address')
    if not address:
        print("No address found in account data")
        return

    try:
        token_class = GetToken(acc['private'], address)
        privy_id_token = token_class.get_auth_token()
        
        if not privy_id_token:
            print(f"Failed to get auth token for {address}")
            return

        headers = {
            "authorization": f"Bearer {privy_id_token}",
            "origin": "https://monad.fantasy.top",
            "referer": "https://monad.fantasy.top/",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        }

        # Get basic info first
        basic_info_url = f"https://secret-api.fantasy.top/player/basic-data/{address}"
        response = requests.get(basic_info_url, headers=headers)
        
        if response.status_code not in (200,201):
            print(f"Failed to get basic info: {response.status_code} - {response.text}")
            return

        basic_info = response.json()
        player_data = basic_info.get('players_by_pk', {})
        fragments = int(player_data.get('fragments', 0))
        
        batch_spins = math.floor(fragments/485)
        print(f"Account {address} has {fragments} fragments -> {batch_spins} spins available")

        # Process spins
        for i in range(batch_spins):
            response = requests.post(spin_url, headers=headers)
            
            if response.status_code not in (200, 201):
                print(f"Spin failed: {response.status_code} - {response.text}")
                continue

            data = response.json()
            selected = data.get("selectedPrizes", [])
            fan_rewards = [int(item["text"]) for item in selected if item.get("type") == "FAN"]
            total_xp = sum(fan_rewards)

            # Log results
            log_entry = {
                "address": address,
                "timestamp": datetime.utcnow().isoformat(),
                "rewards": selected,
                "xp_gained": total_xp,
            }

            update_rewards_log(log_entry)
            print(f"Spin {i+1}/{batch_spins}: Gained {total_xp} XP")
            time.sleep(0.2)

    except Exception as e:
        print(f"Error processing account {address}: {str(e)}")

def update_rewards_log(entry):
    """Handle logging of rewards with thread-safe file operations"""
    file_path = "rewards.json"
    try:
        # Initialize empty list if file doesn't exist
        if not os.path.exists(file_path):
            logs = []
        else:
            # Check if file is empty
            if os.path.getsize(file_path) == 0:
                logs = []
            else:
                with open(file_path, 'r') as f:
                    logs = json.load(f)
        
        logs.append(entry)
        
        with open(file_path, 'w') as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        print(f"Error updating rewards log: {str(e)}")
        # Create fresh file if corrupted
        with open(file_path, 'w') as f:
            json.dump([entry], f, indent=2)

def analyze_spins():
    """Analyze collected spin data with proper reward type handling"""
    file_path = "rewards.json"
    
    if not os.path.exists(file_path):
        print("No rewards data found")
        return

    try:
        with open(file_path, 'r') as f:
            logs = json.load(f)

        if not logs:
            print("No spin data available")
            return

        # Initialize counters
        total_spins = len(logs)
        reward_counts = defaultdict(int)
        reward_amounts = defaultdict(int)
        xp_gained = 0

        # Process each spin entry
        for entry in logs:
            xp_gained += entry.get("xp_gained", 0)
            
            for reward in entry.get("rewards", []):
                reward_type = reward.get("type", "UNKNOWN")
                try:
                    amount = int(reward.get("text", "0"))
                except ValueError:
                    amount = 0
                
                reward_counts[reward_type] += 1
                reward_amounts[reward_type] += amount

        # Display analysis results
        print("\n=== Spin Analysis Results ===")
        print(f"Total spins analyzed: {total_spins}")
        print(f"Total XP gained: {xp_gained}")
        
        print("\nReward Distribution:")
        for reward_type in sorted(reward_counts.keys()):
            print(f"{reward_type}:")
            print(f"  Count: {reward_counts[reward_type]}")
            print(f"  Total Amount: {reward_amounts[reward_type]}")
            if reward_counts[reward_type] > 0:
                avg = reward_amounts[reward_type] / reward_counts[reward_type]
                print(f"  Average per reward: {avg:.2f}")

    except json.JSONDecodeError:
        print("Error: Invalid JSON format in rewards file")
    except Exception as e:
        print(f"Error during analysis: {str(e)}")

if __name__ == "__main__":
    accounts = load_accounts()
    
    if not accounts:
        print("No accounts to process")
        exit()

    for acc in accounts:
        print(f"\nProcessing account: {acc['address']}")
        spin(acc)

    analyze_spins()