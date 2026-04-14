import psd_tools
from .type import NpFigure
from .utils import psd_layer_to_NpFigure, composite_figure
from .logg import log


def main(file: str, translation: str = "翻译") -> tuple[NpFigure, list[NpFigure]]:
    """
    加载 PSD 文件并将其中的图层转换为 NpFigure 对象，并将背景图层和翻译图层分开处理

    :param file: 需要处理的 PSD 文件路径
    :type file: str
    :param translation: 包含翻译图层的组名称，默认为 "翻译"
    :type translation: str, optional
    :return: 包含背景图层转换后 NpFigure 对象和所有翻译图层转换后 NpFigure 对象列表的元组
    :rtype: tuple[NpFigure, list[NpFigure]]
    """
    psd: psd_tools.PSDImage = psd_tools.PSDImage.open(file)  # 加载 PSD 文件
    background_figure_list: list[NpFigure] = []
    translation_figure_list: list[NpFigure] = []
    has_translation_layer = False
    for layer in psd:
        # 逐层处理图层，对于翻译图层组，对其子图层进行处理
        if layer.name == translation:
            has_translation_layer = True
            if layer.is_group():
                for sub_layer in layer:  # type: ignore
                    translation_figure_list.append(psd_layer_to_NpFigure(sub_layer))
            else:
                translation_figure_list.append(psd_layer_to_NpFigure(layer))
        else:
            background_figure_list.append(psd_layer_to_NpFigure(layer))
    if not has_translation_layer:
        log.error(f"文件 {file} 中未找到名为 '{translation}' 的翻译图层(组).")

    # 将背景图层列表合成为单图
    background_figure: NpFigure = composite_figure(background_figure_list, psd.size)
    return background_figure, translation_figure_list
