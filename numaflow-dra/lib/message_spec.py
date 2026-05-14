from msgspec import Struct


class BoundingBox(Struct):
    class_id: int | str
    confidence: float
    top_left_x: float
    top_left_y: float
    bottom_right_x: float
    bottom_right_y: float


class Payload(Struct):
    frame_index: int
    original_height: int
    original_width: int
    bounding_boxes: list[BoundingBox] = []
    compressed_frame: bytes | None = None
