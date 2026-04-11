import click
import os
import cv2.typing
from rich.progress import track
import cv2
import numpy as np
import tempfile
import shutil
from .utils import time_analysis, NpFigure_resize_in_background, composite_figure
from .type import NpFigure


def _to_video_frame(
    figure: cv2.typing.MatLike, width: int, height: int
) -> cv2.typing.MatLike:
    """将任意输入帧规范为视频可写入的 BGR 三通道帧。"""
    if figure.shape[1] != width or figure.shape[0] != height:
        figure = cv2.resize(figure, (width, height), interpolation=cv2.INTER_LINEAR)

    if figure.dtype != np.uint8:
        figure = np.clip(figure, 0, 255).astype(np.uint8)

    if len(figure.shape) == 2:
        return cv2.cvtColor(figure, cv2.COLOR_GRAY2BGR)

    channels = figure.shape[2]
    if channels == 4:
        return cv2.cvtColor(figure, cv2.COLOR_BGRA2BGR)
    if channels == 3:
        return figure

    raise ValueError(f"不支持的图像通道数: {channels}")


def add_figure(
    video: cv2.VideoWriter,
    figure: cv2.typing.MatLike,
    frame: int,
    width: int,
    height: int,
):
    """向视频中添加figure，持续frame帧"""
    bgr_figure = _to_video_frame(figure, width, height)
    for _ in range(frame):
        video.write(bgr_figure)


def _create_video_writer(
    output_path: str, rate: int, size: tuple[int, int]
) -> tuple[cv2.VideoWriter, str]:
    """初始化可用的视频编码器，优先 MP4 常见编码。"""
    for codec in ("mp4v", "avc1", "H264"):
        writer = cv2.VideoWriter(
            output_path,
            cv2.VideoWriter.fourcc(*codec),
            rate,
            size,
        )
        if writer.isOpened():
            return writer, codec
        writer.release()

    raise RuntimeError("无法初始化视频编码器（已尝试 mp4v/avc1/H264），请检查 OpenCV/FFmpeg 编码支持。")


@click.command()
@click.option("--input", "-i", default="input.psd", help="输入的 PSD 文件路径.")
@click.option("--rate", "-r", default=24, help="视频帧率.")
@click.option("--interval", "-l", default="10s", help="图片持续时间.")
@click.option("--transit", "-t", default="500ms", help="图片过渡时间.")
@click.option("--width", "-w", default=-1, help="视频宽度, -1表示自动计算.")
@click.option("--height", "-h", default=-1, help="视频高度, -1表示自动计算.")
@click.option(
    "--group", "-g", default="翻译", help="包含翻译图层的组名称，默认为 '翻译'"
)
def main(
    input: str = "input.psd",
    rate: int = 24,
    interval: str = "10s",
    transit: str = "500ms",
    width: int = -1,
    height: int = -1,
    group: str = "翻译",
):
    assert os.path.isfile(input), f"输入文件 {input} 不存在。"
    assert input.lower().endswith(".psd"), f"输入文件 {input} 不是 PSD 文件。"
    interval_rate = time_analysis(interval) * rate // (1000 * 1000)
    transit_rate = time_analysis(transit) * rate // (1000 * 1000)
    from .psd2figure import main as psd2figure_main

    background_figure, translation_figure_list = psd2figure_main(
        input, translation=group
    )
    if width == -1 and height == -1:
        height, width = background_figure["fig"].shape[:2]
    elif width == -1:
        width = int(
            background_figure["fig"].shape[1]
            * height
            / background_figure["fig"].shape[0]
        )
    elif height == -1:
        height = int(
            background_figure["fig"].shape[0]
            * width
            / background_figure["fig"].shape[1]
        )

    translation_figure_list = [
        NpFigure_resize_in_background(fig, (width, height), old_size=background_figure["fig"].shape[1::-1])
        for fig in translation_figure_list
    ]
    background_figure = NpFigure_resize_in_background(
        background_figure, (width, height)
    )
    work_path, file_name = os.path.split(os.path.abspath(input))
    tmp_file, tmp_path = tempfile.mkstemp(suffix=".mp4")
    os.close(tmp_file)
    video, codec = _create_video_writer(tmp_path, rate, (width, height))

    video.write(_to_video_frame(background_figure["fig"], width, height))
    for figure in track(
        translation_figure_list,
        description="正在生成视频...",
        total=len(translation_figure_list),
    ):
        for transit_rate_index in range(transit_rate):
            rate_fig = figure["fig"][
                :, -figure["fig"].shape[1] * (transit_rate_index + 1) // transit_rate :, :
            ]
            old_bbox = figure["bbox"]
            new_bbox = (
                old_bbox[2] - rate_fig.shape[1],
                old_bbox[1],
                old_bbox[2],
                old_bbox[3],
            )
            video.write(
                _to_video_frame(
                    composite_figure(
                        [NpFigure(fig=rate_fig, bbox=new_bbox)],
                        bg_fig=background_figure["fig"],
                    )["fig"],
                    width,
                    height,
                )
            )

        background_figure = composite_figure([figure], bg_fig=background_figure["fig"])
        add_figure(video, background_figure["fig"], interval_rate, width, height)

    video.release()
    output_name = f"{os.path.splitext(file_name)[0]}_output.mp4"
    shutil.move(
        tmp_path, os.path.join(work_path, output_name)
    )
    print(f"视频已导出: {output_name} (codec={codec})")
