import random


class RandomNumberGenerator:
    def __init__(self, start, end):
        self.numbers = list(range(start, end + 1))

    def get_random_number(self):
        if not self.numbers:
            return None  # 所有数字都已经被选择完毕
        index = random.randint(0, len(self.numbers) - 1)
        random_number = self.numbers.pop(index)
        return random_number
