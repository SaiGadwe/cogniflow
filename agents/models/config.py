import os
from dotenv import find_dotenv, load_dotenv
from uagents_core.identity import Identity

load_dotenv(find_dotenv())

DIRECTOR_SEED = os.getenv("DIRECTOR_SEED")
RHYTHM_SEED = os.getenv("RHYTHM_SEED")
SYNC_SEED = os.getenv("SYNC_SEED")
INSIGHT_SEED = os.getenv("INSIGHT_SEED")

ASI1_API_KEY = os.getenv("ASI1_API_KEY")

DIRECTOR_ADDRESS = Identity.from_seed(seed=DIRECTOR_SEED, index=0).address
RHYTHM_ADDRESS = Identity.from_seed(seed=RHYTHM_SEED, index=0).address
SYNC_ADDRESS = Identity.from_seed(seed=SYNC_SEED, index=0).address
INSIGHT_ADDRESS = Identity.from_seed(seed=INSIGHT_SEED, index=0).address