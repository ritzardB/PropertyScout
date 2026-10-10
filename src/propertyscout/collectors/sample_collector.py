from propertyscout.models import PropertyListing 
from propertyscout.sample_data import SAMPLE_LISTINGS


def collect_properties() -> list[PropertyListing]:
    """
    Collects property listings from the sample data.

    Returns:
        list[PropertyListing]: A list of PropertyListing objects.
    """
    print("Collecting demonstration property records...") 
    return SAMPLE_LISTINGS


