class ResourceBank:
    def __init__(self, start_credits: int = 100):
        self.credits = start_credits
        self.scrap = 0

    def spend(self, amount: int) -> bool:
        if self.credits >= amount:
            self.credits -= amount
            return True
        return False

    def add_reward(self, amount: int):
        self.credits += amount
        print(f"+{amount} credits. Total: {self.credits}")