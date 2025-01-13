from dataclasses import dataclass

@dataclass
class AdminRights:
    def __init__(self, company):
        self.company = company

        self.blanket_dict = {
            'Altice': 'Altice',
            'American Airlines': 'American Airlines',
            'Apple': 'Apple',
            'Church Mutual': 'Church Mutual',
            'Church of Christ': 'Church of Christ',
            'Do It Best': 'Do It Best',
            'Frontier': 'Frontier',
            'Disney': 'Disney',
            'LSD Saints': 'LSD saints',
            'Microsoft': 'MSFT',
            'Petsmart': 'Petsmart'
        }

    def check_blanket(self):
        company = self.company.lower()

        if company in {key.lower() for key in self.blanket_dict.keys()}:
            return True
        
        if self.company.lower() in {values.lower() for values in self.blanket_dict.values()}:
            return True

        return False