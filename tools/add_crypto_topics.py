import json

new_crypto_blockchain_topics = [
    # Future of Money & Digital Currency Revolution
    "future of crypto and digital money 2030",
    "future of cryptocurrency global financial system",
    "how cryptocurrency will change future banking",
    "can governments ban cryptocurrency reality",
    "how governments try to block crypto transactions",
    "cbdc vs decentralized cryptocurrency privacy battle",
    "central bank digital currency privacy surveillance",
    "death of physical paper cash future",
    "global dedollarization digital currency reserve",
    "hyperinflation fiat currency collapse hedge",
    "programmable money smart contracts economy",
    "crypto regulation global ban crackdown future",
    "how secret crypto transactions work ledger",
    "crypto black swan event financial collapse",

    # Blockchain Architecture, Tech & Cryptography
    "how blockchain technology actually works simply",
    "blockchain scalability trilemma decentralized secure fast",
    "zero knowledge proofs privacy cryptography explained",
    "zk snarks mathematical privacy verification",
    "layer 2 rollup technology scaling transactions",
    "sharding blockchain horizontal database partition",
    "proof of work vs proof of stake consensus mechanism",
    "byzantine fault tolerance distributed consensus",
    "decentralized autonomous organization dao governance",
    "smart contracts self executing code vulnerabilities",
    "blockchain cross chain atomic swap bridge",
    "quantum computing threat to blockchain cryptography",
    "post quantum cryptography blockchain security",
    "51 percent attack blockchain consensus vulnerability",
    "mev maximal extractable value frontrunning blockchain",

    # Decentralized Finance (DeFi) & Web3 Infrastructure
    "decentralized finance defi future banking replacement",
    "automated market maker liquidity pool mechanism",
    "flash loans uncollateralized instant borrowing exploit",
    "decentralized identity self sovereign identity did",
    "decentralized storage ipfs permanent web",
    "decentralized physical infrastructure depin networks",
    "decentralized computing render ai gpu compute crypto",
    "oracle problem chainlink real world data smart contract",
    "tokenomics inflation burn mechanism economics",
    "real world asset rwa tokenization trillions",
    "tokenized real estate treasury bills on blockchain",

    # AI + Blockchain Synergy & Autonomous Economy
    "ai agents with cryptocurrency crypto wallet autonomy",
    "ai paying other ai microtransactions crypto",
    "decentralized artificial intelligence compute networks",
    "verifying ai generated content on blockchain cryptographic",
    "ai trading bots crypto arbitrage high frequency",

    # Web3 Security, Cold Wallets & Privacy Tech
    "hardware wallet seed phrase cold storage security",
    "multisig wallet security institutional crypto storage",
    "crypto mixer tornado cash privacy law enforcement",
    "blockchain forensic analysis tracking wallets",
    "smart contract audit reentrancy attack flash loan hack",
    "crypto quantum hack prediction sha256 vulnerability",
    "lost crypto permanently lost private keys burn",
    "satoshi nakamoto mystery identity cypherpunk movement",
    "crypto halving economic supply shock cycle",
    "future of web3 decentralized internet protocol"
]

file_path = "data/viral_topics.json"
with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

existing = set(data.get("keywords", []))
added = [t for t in new_crypto_blockchain_topics if t not in existing]
data["keywords"].extend(added)

with open(file_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Added {len(added)} new future crypto & blockchain topics. Total: {len(data['keywords'])}")
