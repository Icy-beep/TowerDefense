class ResourceBank:
    """Хранит кредиты игрока."""

    def __init__(self, start_credits: int = 1000):
        """Создаёт банк с начальным количеством кредитов."""
        self.credits = start_credits
        self.scrap = 0

    def spend(self, amount: int) -> bool:
        """Списывает кредиты, если их достаточно."""
        if self.credits >= amount:
            self.credits -= amount
            return True
        return False

    def spend_scrap(self, amount: int) -> bool:
        """Списывает scrap, если его достаточно (см. GameSession.upgrade_tech_branch)."""
        if self.scrap >= amount:
            self.scrap -= amount
            return True
        return False

    def add_reward(self, amount: int):
        """Начисляет кредиты за убитого врага."""
        self.credits += amount
        print(f"+{amount} credits. Total: {self.credits}")

    def add_scrap(self, amount: int):
        """Начисляет scrap за убитого врага фракции Corporation (см.
        HostileEntity.scrap_reward, GameSession.update)."""
        self.scrap += amount
        print(f"+{amount} scrap. Total: {self.scrap}")