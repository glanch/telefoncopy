from dataclasses import dataclass



@dataclass
class Contact:
    name: str
    number: tuple[int|str]
    greeting_path: str

    def __str__(self):
        return f"{self.name} ({self.number})"

    def __repr__(self):
        return f"Contact(name={self.name}, number={self.number})"


def was_dialed(number: tuple[int|str], contacts: list[Contact]) -> Contact | None:
    for contact in contacts:
        if contact.number == number:
            return contact
    return None
