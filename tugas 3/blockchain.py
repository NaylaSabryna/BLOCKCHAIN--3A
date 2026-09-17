from block import Block


class Blockchain:

  def __init__(self):
    self.chain = [self.create_genesis_block()]

  def create_genesis_block(self):
    return Block(0, {"message": "Genesis Block - E-Voting System"}, "0")

  def add_block(self, data: dict):
    previous_block = self.chain[-1]
    new_block = Block(
        index=len(self.chain), data=data, previous_hash=previous_block.hash
    )
    self.chain.append(new_block)

  def is_valid(self) -> bool:
    for i in range(1, len(self.chain)):
      current = self.chain[i]
      previous = self.chain[i - 1]

      if current.hash != current.calculate_hash():
        return False
      if current.previous_hash != previous.hash:
        return False
    return True

  def show(self):
    for block in self.chain:
      print(f"--- Block {block.index} ---")
      print(f"Timestamp    : {block.timestamp}")
      print(f"Vote Data    : {block.data}")
      print(f"Previous Hash: {block.previous_hash}")
      print(f"Nonce        : {block.nonce}")
      print(f"Hash         : {block.hash}\n")