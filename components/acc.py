import os
from dotenv import load_dotenv

load_dotenv()

def get_accs():
    return os.getenv("sn_u"), os.getenv("sn_p")