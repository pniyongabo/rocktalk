import base64
from io import BytesIO

from PIL import Image, ImageFile

MAX_IMAGE_WIDTH: int = 300


def image_from_b64_image(b64_image: str) -> ImageFile.ImageFile:
    """Convert a base64-encoded image string to a PIL Image object.

    Args:
        b64_image (str): Base64-encoded image string.
    Returns:
        ImageFile.ImageFile: PIL Image object.
    """

    image_data: bytes = base64.b64decode(b64_image)
    image: ImageFile.ImageFile = Image.open(BytesIO(image_data))
    return image
