from dotenv import load_dotenv
import os

load_dotenv(verbose=True)



CHAIN_ID = int(os.getenv("CHAIN_ID", "1"))
NETWORK = os.getenv("NETWORK", "")
ENDPOINT_URI = os.getenv("ENDPOINT_URI", "")
PRIV_KEY = os.getenv("PRIV_KEY", "")
