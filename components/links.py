from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Links:
    dashboard = os.getenv('dashboard')
    vtb = os.getenv('vtb')
    user_list = os.getenv('user_list')
    user_create = os.getenv('user_create')