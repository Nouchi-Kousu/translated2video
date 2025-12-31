import click
import os
import cv2.typing
from rich.progress import track
from rich import print
import cv2
import numpy as np


def cover(
    background: cv2.typing.MatLike, figure: cv2.typing.MatLike
) -> cv2.typing.MatLike:
    """使用figure覆盖background，右上角对齐"""
    fg_h, fg_w = figure.shape[:2]
    fg_alpha = figure[:, :, 3] / 255.0
    bg_alpha = 1.0 - fg_alpha
    background = background.copy()
    background[:fg_h, -fg_w:] = (
        background[:fg_h, -fg_w:] * bg_alpha[:, :, None]
        + figure[:, :, :3] * fg_alpha[:, :, None]
    )
    return background


def add_figure(video: cv2.VideoWriter, figure: cv2.typing.MatLike, frame: int):
    """向视频中添加figure，持续frame帧"""
    for _ in range(frame):
        video.write(figure)


@click.command()
@click.option("--rate", "-r", default=24, help="视频帧率.")
@click.option("--interval", "-i", default=10, help="图片持续时间（秒）.")
@click.option("--transit", "-t", default=500, help="图片过渡时间（毫秒）.")
@click.option("--width", "-w", default=-1, help="视频宽度, -1表示自动计算.")
@click.option("--height", "-h", default=-1, help="视频高度, -1表示自动计算.")
def main(rate, interval, transit, width, height):
    rate = int(rate)
    interval = int(interval) * rate
    transit = int(int(transit) / 1000.0 * rate)
    width = int(width)
    height = int(height)
    path = os.getcwd()
    figure_list = [
        os.path.join(path, f) for f in os.listdir(path) if f.endswith(".png")
    ]
    figure_list.sort()
    figure_list = [cv2.imdecode(np.fromfile(f, dtype=np.uint8), cv2.IMREAD_UNCHANGED) for f in figure_list]
    raw_height, raw_width = figure_list[0].shape[:2]

    if width == -1 and height == -1:
        width, height = raw_width, raw_height
    elif width == -1:
        width = int(raw_width * (height / raw_height))
    elif height == -1:
        height = int(raw_height * (width / raw_width))

    figure_list = [
        cv2.resize(f, (width, height), interpolation=cv2.INTER_LINEAR)
        for f in figure_list
    ]

    video = cv2.VideoWriter(
        f"./{os.path.basename(path)}.mp4",
        cv2.VideoWriter.fourcc(*"mp4v"),
        rate,
        (width, height),
    )

    # 创建画布
    video_figure = figure_list[0].copy()
    # 添加第一张图片（无过渡）
    add_figure(video, video_figure, interval)
    # 添加后续图片（有过渡）
    for i in track(range(1, len(figure_list)), description="正在生成视频..."):
        figure = figure_list[i]
        for j in range(transit):
            cover_width = (j + 1) * width // transit
            video.write(cover(video_figure, figure[:, -cover_width:]))
        video_figure = cover(video_figure, figure)
        add_figure(video, video_figure, interval)

    video.release()

    print("[bold green]视频生成完成！[/bold green]")
