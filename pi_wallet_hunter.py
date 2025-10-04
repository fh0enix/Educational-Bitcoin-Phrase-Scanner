"""
Educational / controlled version:
- supports random order, modes (shuffle_phrases, random_year, infinite_random),
- exponential backoff for HTTP requests,
- multiprocessing,
- saves to files found_words.txt / active_words.txt,
- by default DOES NOT make network requests (ENABLE_NETWORK = False).
WARNING: if ENABLE_NETWORK = True — use only for your own addresses or on testnet.
"""

import hashlib, base58, requests, datetime, time, random, os
from multiprocessing import Process, Lock, cpu_count
from ecdsa import SigningKey, SECP256k1
from typing import Any

# ----------------- Configuration (set carefully) -----------------
WORDLIST_URL = "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"
YEARS = list(range(1903, 2014))  # 1903–2014

# Safe defaults:
ENABLE_NETWORK = False      # <<< by default False — do not make network requests
USE_TESTNET = False         # if ENABLE_NETWORK=True, USE_TESTNET=True → test network
MODE = "shuffle_phrases"    # "shuffle_phrases" | "random_year" | "infinite_random"
NUM_PROCS = min(cpu_count(), 4)
RANDOM_YEARS_PER_WORD = 10  # for "random_year" mode
SAVE_PRIVATE = False        # save private key to file (NOT recommended)
RATE_SLEEP = 0.05           # base sleep between requests
# -------------------------------------------------------------------

def fetch_wordlist():
    r = requests.get(WORDLIST_URL, timeout=10)
    r.raise_for_status()
    return [w.strip() for w in r.text.splitlines() if w.strip()]

def phrase_to_priv(phrase: str) -> bytes:
    return hashlib.sha256(phrase.encode()).digest()

def priv_to_wif(priv_bytes: bytes) -> str:
    payload = b'\x80' + priv_bytes  # mainnet WIF prefix
    chk = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return base58.b58encode(payload + chk).decode()

def priv_to_addr(priv: bytes, testnet: bool = False) -> str:
    # Simple P2PKH implementation (non-compressed public key)
    pub = b'\x04' + SigningKey.from_string(priv, curve=SECP256k1).verifying_key.to_string()
    sha = hashlib.sha256(pub).digest()
    rip = hashlib.new('ripemd160', sha).digest()
    prefix = b'\x6f' if testnet else b'\x00'  # testnet prefix 0x6f, mainnet 0x00
    pl = prefix + rip
    chk = hashlib.sha256(hashlib.sha256(pl).digest()).digest()[:4]
    return base58.b58encode(pl + chk).decode()

def _http_get_with_backoff(url, timeout=6, max_attempts=3):
    backoff = 1.0
    for attempt in range(1, max_attempts + 1):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:
            if attempt == max_attempts:
                raise
            time.sleep(backoff)
            backoff *= 2

def check_addr(addr: str):
    """
    If ENABLE_NETWORK=False -> returns (0.0, False) (simulation).
    If ENABLE_NETWORK=True -> makes request to Blockstream API (mainnet or testnet),
    with exponential backoff.
    WARNING: use only for your own addresses or in test networks.
    """
    if not ENABLE_NETWORK:
        # Safe simulation — network disabled
        return 0.0, False

    base = "https://blockstream.info/testnet/api" if USE_TESTNET else "https://blockstream.info/api"
    url = f"{base}/address/{addr}"
    try:
        r = _http_get_with_backoff(url, timeout=8, max_attempts=4)
        d = r.json()
        funded = d.get("chain_stats", {}).get("funded_txo_sum", 0)
        spent = d.get("chain_stats", {}).get("spent_txo_sum", 0)
        memf = d.get("mempool_stats", {}).get("funded_txo_sum", 0)
        mems = d.get("mempool_stats", {}).get("spent_txo_sum", 0)
        balance = (funded - spent + memf - mems) / 1e8
        active = d.get("chain_stats", {}).get("tx_count", 0) > 0
        return balance, active
    except Exception as e:
        # If connection error — assume address has no balance
        return 0.0, False

def save(lock: Any, fn: str, phrase: str, priv: bytes, addr: str, bal: float, active: bool):
    ts = datetime.datetime.now().isoformat(sep=' ', timespec='seconds')
    with lock:
        with open(fn, "a", encoding="utf-8") as f:
            if SAVE_PRIVATE:
                try:
                    wif = priv_to_wif(priv)
                except Exception:
                    wif = "<wif-error>"
                f.write(f"[{ts}] {phrase} | {addr} | {bal} BTC | active:{active} | wif:{wif}\n")
            else:
                f.write(f"[{ts}] {phrase} | {addr} | {bal} BTC | active:{active}\n")

def generate_phrases(base_word: str):
    phrases = []
    for year in YEARS:
        phrases.append(f"{base_word}{year}")
        phrases.append(f"{base_word}{str(year)[2:]}")
    return phrases

def worker(lock: Any, words, wid: int, mode: str = "shuffle_phrases"):
    if mode not in ("shuffle_phrases", "random_year", "infinite_random"):
        mode = "shuffle_phrases"

    for i, word in enumerate(words, start=1):
        if mode == "shuffle_phrases":
            phrases = generate_phrases(word)
            random.shuffle(phrases)
            iterable = phrases
        elif mode == "random_year":
            iterable = []
            for _ in range(RANDOM_YEARS_PER_WORD):
                y = random.choice(YEARS)
                yfmt = y if random.choice((True, False)) else str(y)[2:]
                iterable.append(f"{word}{yfmt}")
        elif mode == "infinite_random":
            # infinite random mode — runs until manually stopped
            while True:
                y = random.choice(YEARS)
                yfmt = y if random.choice((True, False)) else str(y)[2:]
                phrase = f"{random.choice(words)}{yfmt}"
                priv = phrase_to_priv(phrase)
                addr = priv_to_addr(priv, testnet=USE_TESTNET)
                bal, act = check_addr(addr)
                print(f"[W{wid}] INF '{phrase}' → Bal: {bal}, Act: {act}")
                if bal > 0:
                    save(lock, "found_words.txt", phrase, priv, addr, bal, act)
                elif act:
                    save(lock, "active_words.txt", phrase, priv, addr, bal, act)
                time.sleep(RATE_SLEEP)
            return
        else:
            iterable = generate_phrases(word)

        for phrase in iterable:
            priv = phrase_to_priv(phrase)
            addr = priv_to_addr(priv, testnet=USE_TESTNET)
            bal, act = check_addr(addr)
            print(f"[W{wid}] {i}/{len(words)} '{phrase}' → Bal: {bal}, Act: {act}")
            if bal > 0:
                save(lock, "found_words.txt", phrase, priv, addr, bal, act)
            elif act:
                save(lock, "active_words.txt", phrase, priv, addr, bal, act)
            time.sleep(RATE_SLEEP)

def main():
    print("[ℹ] Starting (educational version).")
    print(f"[ℹ] ENABLE_NETWORK={ENABLE_NETWORK}, USE_TESTNET={USE_TESTNET}, MODE={MODE}, NUM_PROCS={NUM_PROCS}")
    # Load wordlist
    words = fetch_wordlist()
    print(f"[ℹ] Loaded {len(words):,} words")

    # Shuffle words for random order processing
    random.shuffle(words)

    # Split words into chunks for processes
    num = NUM_PROCS
    chunks = [words[i::num] for i in range(num)]
    lock = Lock()

    procs = [Process(target=worker, args=(lock, chunk, idx+1, MODE)) for idx, chunk in enumerate(chunks)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()

if __name__ == "__main__":
    main()
