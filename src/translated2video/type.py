from typing import TypedDict

import cv2
import numpy as np


class NpFigure(TypedDict):
    fig: cv2.typing.MatLike
    bbox: tuple[int, int, int, int]  # x_start, y_start, x_end, y_end