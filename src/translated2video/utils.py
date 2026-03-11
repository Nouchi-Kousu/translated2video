from PIL.Image import Image
import cv2
from cv2.typing import MatLike
import numpy as np
import psd_tools.api.layers
from .type import NpFigure, BBox


# COLOR_MODE = {
#     0: "BITMAP",
#     1: "GRAYSCALE",
#     2: "INDEXED",
#     3: "RGB",
#     4: "CMYK",
#     7: "MULTICHANNEL",
#     8: "DUOTONE",
#     9: "LAB",
# }


def psd_layer_to_NpFigure(layer: psd_tools.api.layers.Layer) -> NpFigure:
    """
    将 PSD 图层（RGBA）转换为 NpFigure 对象（BGRA）

    :param layer: 需要转换的 PSD 图层
    :type layer: psd_tools.api.layers.Layer
    :return: 转换后的 NpFigure 对象
    :rtype: NpFigure
    """
    figure: Image | None = layer.composite()
    if figure is None:
        raise ValueError(f"Layer '{layer.name}' could not be rendered.")

    # 将 PIL Image 转换为 NumPy 数组，并确保包含 alpha 通道
    np_figure: np.ndarray = np.array(figure.convert("RGBA"))

    return NpFigure(
        fig=np_figure[:, :, [2, 1, 0, 3]],  # (R, G, B, A) -> (B, G, R, A)
        bbox=layer.bbox,
    )


def NpFigure_resize_in_background(
    figure: NpFigure,
    new_size: tuple[int, int],
    old_size: tuple[int, int] | None = None,
    interpolation: int = cv2.INTER_LINEAR,
) -> NpFigure:
    """
    将 NpFigure 贴在背景图层后调整大小，
    保持图层相对位置与相对大小不变，
    返回调整大小后的 NpFigure 对象（无背景）

    :param figure: 需要调整大小的 NpFigure 对象
    :type figure: NpFigure
    :param new_size: 背景图的新尺寸 (宽, 高)
    :type new_size: tuple[int, int]
    :param old_size: 背景图的旧尺寸 (宽, 高), 默认为 None，表示使用 figure 的 bbox 大小作为旧尺寸
    :type old_size: tuple[int, int] | None
    :param interpolation: 插值方法，参见 cv2 的插值方法
    :type interpolation: int
    :return: 调整大小后的 NpFigure 对象
    :rtype: NpFigure
    """
    bbox: BBox = figure["bbox"]
    figure_size: tuple[int, int] = figure["fig"].shape[1], figure["fig"].shape[0]
    old_size = (
        old_size if old_size is not None else (bbox[2] - bbox[0], bbox[3] - bbox[1])
    )  # 如果未提供旧尺寸，则使用 figure 的 bbox 大小作为旧尺寸
    figure_new_size: tuple[int, int] = (
        int(figure_size[0] * new_size[0] / old_size[0]),
        int(figure_size[1] * new_size[1] / old_size[1]),
    )  # 计算 figure 的新尺寸，保持相对大小不变
    new_bbox: BBox = (
        int(bbox[0] * new_size[0] / old_size[0]),
        int(bbox[1] * new_size[1] / old_size[1]),
        bbox[0] + figure_new_size[0],
        bbox[1] + figure_new_size[1],
    )  # 计算 figure 的新 bbox，保持相对位置不变

    resized_fig: MatLike = cv2.resize(
        figure["fig"], figure_new_size, interpolation=interpolation
    )
    return NpFigure(fig=resized_fig, bbox=new_bbox)


def composite_figure(
    figure_list: list[NpFigure],
    bg_size: tuple[int, int] | None = None,
    bg_fig: MatLike | None = None,
) -> NpFigure:
    """
    合成 NpFigure 对象列表为单个 NpFigure 对象，支持指定合成画布为某图或指定尺寸画布

    :param figure_list: 需要合成的 NpFigure 对象列表
    :type figure_list: list[NpFigure]
    :param bg_size: 画布尺寸 (宽, 高)
    :type bg_size: tuple[int, int] | None
    :param bg_fig: 背景图层的 NpFigure 对象
    :type bg_fig: cv2.typing.MatLike | None
    :return: 合成后的 NpFigure 对象
    :rtype: NpFigure
    """
    if bg_fig is None and bg_size is not None:
        background_fig: np.ndarray = np.zeros((bg_size[1], bg_size[0], 4), dtype=np.uint8)
        size: tuple[int, int] = bg_size
    elif bg_fig is not None and bg_size is None:
        background_fig: np.ndarray = bg_fig
        size: tuple[int, int] = (background_fig.shape[1], background_fig.shape[0])
    else:
        raise ValueError("bg_size 和 bg_fig 必须且只能设置一个。")

    for figure in figure_list:
        bbox: BBox = figure["bbox"]
        # 调整 bbox 以适应背景图层的尺寸，确保不会超出背景图层的边界
        if bbox[2] > size[0]:
            bbox: BBox = (bbox[0], bbox[1], size[0], bbox[3])
        if bbox[3] > size[1]:
            bbox: BBox = (bbox[0], bbox[1], bbox[2], size[1])
        start: tuple[int, int] = (0, 0)
        if bbox[0] < 0:
            start: tuple[int, int] = (-bbox[0], start[1])
            bbox: BBox = (0, bbox[1], bbox[2], bbox[3])
        if bbox[1] < 0:
            start: tuple[int, int] = (start[0], -bbox[1])
            bbox: BBox = (bbox[0], 0, bbox[2], bbox[3])

        fg_h, fg_w = bbox[3] - bbox[1], bbox[2] - bbox[0]
        # 使用 alpha 通道进行前景与背景的合成，确保合成结果不会超出背景图层的边界
        fg_alpha: np.ndarray = (
            figure["fig"][start[1] : start[1] + fg_h, start[0] : start[0] + fg_w, 3]
            / 255.0
        )
        bg_alpha: np.ndarray = 1.0 - fg_alpha
        background_fig[bbox[1] : bbox[1] + fg_h, bbox[0] : bbox[0] + fg_w] = (
            background_fig[bbox[1] : bbox[1] + fg_h, bbox[0] : bbox[0] + fg_w]
            * bg_alpha[:, :, None]
            + figure["fig"][start[1] : start[1] + fg_h, start[0] : start[0] + fg_w]
            * fg_alpha[:, :, None]
        )

    return NpFigure(fig=background_fig, bbox=(0, 0, size[0], size[1]))