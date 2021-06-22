from faker import Faker
from spectrum2.protocol_pb2 import (
    Buddy, Buddies
)


def generate_buddy(faker: Faker) -> Buddy:
    """
    Generate a fake buddy.
    """
    return Buddy(
        userName=faker.user_name(),
        buddyName=faker.user_name(),

    )

def generate_buddies(faker: Faker, count: int = 10) -> Buddies:
    """
    Generate fake buddies
    """
    return Buddies(buddy=[generate_buddy(faker) for _ in range(count)])