from concurrent.futures import ProcessPoolExecutor
import click
import os
import cv2.typing
from rich.progress import Progress
import cv2
import numpy as np
import tempfile
import shutil
from .utils import time_analysis, NpFigure_resize_in_background, composite_figure
from .type import NpFigure
import multiprocessing
from .logg import log


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

    raise RuntimeError(
        "无法初始化视频编码器（已尝试 mp4v/avc1/H264），请检查 OpenCV/FFmpeg 编码支持。"
    )


def process_psd(
    psd_path: str,
    group_name: str = "翻译",
    width: int = -1,
    height: int = -1,
) -> tuple[NpFigure, list[NpFigure]]:
    from .psd2figure import main as psd2figure_main

    background_figure, translation_figure_list = psd2figure_main(
        psd_path, translation=group_name
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
        NpFigure_resize_in_background(
            fig, (width, height), old_size=background_figure["fig"].shape[1::-1]
        )
        for fig in translation_figure_list
    ]
    background_figure = NpFigure_resize_in_background(
        background_figure, (width, height)
    )

    return background_figure, translation_figure_list


def create_video(
    background_figure: NpFigure,
    translation_figure_list: list[NpFigure],
    rate: int,
    interval_rate: int,
    transit_rate: int,
    psd_path: str,
    queue,
):
    width, height = background_figure["fig"].shape[1], background_figure["fig"].shape[0]
    work_path, file_name = os.path.split(os.path.abspath(psd_path))
    tmp_file, tmp_path = tempfile.mkstemp(suffix=".mp4")
    os.close(tmp_file)
    video, codec = _create_video_writer(tmp_path, rate, (width, height))

    video.write(_to_video_frame(background_figure["fig"], width, height))
    for figure in translation_figure_list:
        for transit_rate_index in range(transit_rate):
            rate_fig = figure["fig"][
                :,
                -figure["fig"].shape[1] * (transit_rate_index + 1) // transit_rate :,
                :,
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
        queue.put((psd_path, 1))

    video.release()
    output_name = f"{os.path.splitext(file_name)[0]}_output.mp4"
    shutil.move(tmp_path, os.path.join(work_path, output_name))


@click.command()
@click.option(
    "--input", "-i", default=["."], help="输入的 PSD 文件路径.", multiple=True
)
@click.option("--rate", "-r", default=24, help="视频帧率.")
@click.option("--interval", "-l", default="10s", help="图片持续时间.")
@click.option("--transit", "-t", default="500ms", help="图片过渡时间.")
@click.option("--width", "-w", default=-1, help="视频宽度, -1表示自动计算.")
@click.option("--height", "-h", default=-1, help="视频高度, -1表示自动计算.")
@click.option(
    "--group", "-g", default="翻译", help="包含翻译图层的组名称，默认为 '翻译'"
)
def main(
    input: list[str] = ["input.psd"],
    rate: int = 24,
    interval: str = "10s",
    transit: str = "500ms",
    width: int = -1,
    height: int = -1,
    group: str = "翻译",
):
    return_mark = False
    for i in input:
        if not os.path.exists(i):
            return_mark = True
            log.error(f"输入路径/文件 {i} 不存在。")
    if return_mark:
        return

    interval_rate = time_analysis(interval) * rate // (1000 * 1000)
    transit_rate = time_analysis(transit) * rate // (1000 * 1000)
    log.info("开始扫描文件")
    input_file_list = [
        f
        for i in input
        for f in (
            [os.path.join(i, i_f) for i_f in os.listdir(i)] if os.path.isdir(i) else [i]
        )
        if f.lower().endswith(".psd")
    ]

    log.info(f"共找到 {len(input_file_list)} 个 PSD 文件，开始读取文件...")
    poll = multiprocessing.Pool()

    figure_list = poll.map(process_psd, input_file_list)
    log.info("文件读取完成，开始处理...")
    with Progress() as progress:
        with multiprocessing.Manager() as manager:
            queue = manager.Queue()

            task_id = {
                f: progress.add_task(f"处理 {os.path.basename(f)}", total=len(figure_list[i][1]))
                for i, f in enumerate(input_file_list)
            }
            with ProcessPoolExecutor() as executor:
                futures = [
                    executor.submit(
                        create_video,
                        background_figure,
                        translation_figure_list,
                        rate,
                        interval_rate,
                        transit_rate,
                        file_name,
                        queue,
                    ) for (background_figure, translation_figure_list), file_name in zip(figure_list, input_file_list)
                ]

                while not all(f.done() for f in futures) or not queue.empty():
                    try:
                        if not queue.empty():
                            file_name, progress_increment = queue.get(timeout=0.1)
                            progress.update(task_id[file_name], advance=progress_increment)
                    except Exception:
                        pass

    log.info("所有文件处理完成，输出视频已保存至对应文件夹。")
