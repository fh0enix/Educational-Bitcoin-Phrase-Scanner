# Educational Bitcoin Phrase Scanner (Controlled Version)

> **WARNING:** This repository contains an **educational** script that generates Bitcoin addresses from `word + year` phrases and can optionally query a blockchain API. **Do not** use this tool to scan, access, or attempt to access other people's wallets or funds — that is illegal and unethical. By default, network requests are **disabled**. If you enable network access (`ENABLE_NETWORK = True`), use it **only** for addresses you own or on a Bitcoin testnet.

---

## 🔎 Overview

This Python script generates Bitcoin P2PKH addresses from simple phrase patterns (word + year or two-digit year), optionally checks address activity and balance via the Blockstream API, and records results. It is intended **only for learning, testing and research**.

Main features:

- Randomized processing order
- Modes: `shuffle_phrases`, `random_year`, `infinite_random`
- Exponential backoff for HTTP requests
- Multiprocessing support (parallel workers)
- Results saved to `found_words.txt` (addresses with balance) and `active_words.txt` (addresses with transaction history)
- Default behavior: **no network requests** (`ENABLE_NETWORK = False`)

---

## ⚠️ Safety & Ethics

- **Do not** enable `ENABLE_NETWORK` to scan or probe addresses you do not own.
- Prefer `USE_TESTNET = True` with `ENABLE_NETWORK = True` when experimenting with network queries.
- `SAVE_PRIVATE = False` by default — the script does **not** save private keys unless you explicitly enable this (not recommended).
- This tool is for educational purposes: learning address derivation, testing flows, or validating logging/IO behavior.

---

## 📁 Repo layout (example)

```
.
├── pi_wallet_hunter.py     # Main script
├── found_words.txt         # Addresses found with non-zero balance (appended)
├── active_words.txt        # Addresses with tx history (appended)
├── README.md               # This file
└── requirements.txt        # Required Python packages
```

---

## ⚙️ Configuration (top of `pi_wallet_hunter.py`)

Edit these values at the top of the script to control behavior:

```python
WORDLIST_URL = "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"
YEARS = list(range(1903, 2014))   # Years appended to words (inclusive range)

ENABLE_NETWORK = False            # False = no network queries (safe default)
USE_TESTNET = False               # If network enabled, use testnet endpoints
MODE = "shuffle_phrases"          # "shuffle_phrases" | "random_year" | "infinite_random"
NUM_PROCS = min(cpu_count(), 4)   # Max number of parallel processes (cap to CPU)
RANDOM_YEARS_PER_WORD = 10        # Number of random years per word (random_year mode)
SAVE_PRIVATE = False              # Save private key (WIF) to file — NOT recommended
RATE_SLEEP = 0.05                 # Pause between address checks to avoid rate pressure
```

### Change years used in generation
Modify the `YEARS` list. Examples:

```python
# Years 1970 through 2000 inclusive
YEARS = list(range(1970, 2001))

# Or a custom list
YEARS = [1969, 1976, 1984, 1999, 2010]
```

---

## 🔧 Installation

1. Clone or copy repository:
```bash
git clone https://github.com/fh0enix/Educational-Bitcoin-Phrase-Scanner.git
cd Educational-Bitcoin-Phrase-Scanner
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

---

## ▶️ Running the script

Run with Python:

```bash
python pi_wallet_hunter.py
```

Default behavior is **offline** (no network). Console output shows worker progress lines such as:

```
[W1] 4/92526 'example1970' → Bal: 0.0, Act: False
```

- `W1` — worker ID
- `4/92526` — progress in that worker's chunk
- `'example1970'` — phrase checked
- `Bal` — balance (BTC)
- `Act` — whether address has transaction history

### Enable live network checks (only for owned/test addresses)
Set in script:
```python
ENABLE_NETWORK = True
USE_TESTNET = True   # strongly recommended for testing
```

Then run the script. Be mindful of API rate limits and legal/ethical constraints.

---

## 📄 Output files

- `found_words.txt` — appended lines for any phrase/address with `balance > 0`
- `active_words.txt` — appended lines for addresses with transactions (`tx_count > 0`)

Line format:
```
[YYYY-MM-DD HH:MM:SS] <phrase> | <address> | <balance> BTC | active:<True/False> | wif:<optional WIF>
```
(`wif` is present only if `SAVE_PRIVATE = True`)

---

## 🛠 Implementation notes

- Private key derivation: the script uses `SHA-256(phrase)` as a simple private key seed (educational only). This is **not** BIP39/BIP32 — do not use for real wallets.
- Address type: simple uncompressed **P2PKH** constructed from the verifying key.
- The script uses the Blockstream Esplora API for address stats when network is enabled.
- The address space is astronomically large; brute-forcing funded addresses is infeasible and unethical.

---

## ✅ Recommended safe workflow (for learning)

1. Keep `ENABLE_NETWORK = False` while testing locally to verify generation logic.
2. If you want to check actual balances for addresses you control, create a test wallet on Bitcoin testnet and set:
```python
ENABLE_NETWORK = True
USE_TESTNET = True
```
3. Consider adding logging rotation or limiting output if running for long periods.
4. **Never** use this tool to try to access others' funds. Doing so may be illegal.

---

## 🐛 Troubleshooting

- **Permission or missing Python**: Ensure `python` or `py -3` is available and points to Python 3.8+.
- **Windows launch errors (`/usr/bin/env`)**: Run the script directly using `python pi_wallet_hunter.py` or configure your editor to use the system Python.
- **Rate limiting**: The script includes exponential backoff—still, keep `RATE_SLEEP` conservative and prefer `USE_TESTNET = True` during tests.
- **Pylance/type hints issues**: If your IDE warns about `Lock` type annotations, remove or simplify the annotation (e.g., `lock: Any` or `lock` only).

---

## 📌 License & Ethics

This project is provided **for educational purposes only**. Use responsibly.

By using this code you agree **not** to use it to scan, access, or attempt to control wallets or funds that you do not own. Attempting to obtain unauthorized access to digital assets may be illegal in your jurisdiction.

---

## 🤝 Contributing

If you'd like improvements (CSV export, testnet helpers, safer logging), open an issue or submit a pull request. Please do not include any sensitive data in commits.
