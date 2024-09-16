from dataclasses import dataclass

@dataclass
class AdminRights:
    # blanket admin rights:
    # american airlines, microsoft, t-mobile, LSD saints/church of christ
    # church mutual (staffing ONLY), do it best, frontier, altice
    # apple, petsmart
    def __init__(self, company):
        self.company = company

        # dictionary of blanket admins.
        self.blanket_dict = {
            'Altice': 'Altice',
            'American Airlines': 'AA',
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
        for key, value in self.blanket_dict.items():
            if self.company.lower() in key.lower() or self.company.lower() in value.lower():
                return True

        return False