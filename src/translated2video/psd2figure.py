import psd_tools
from .type import NpFigure
from .utils import psd_layer_to_NpFigure, composite_figure


def main(file: str, translation: str = "翻译") -> tuple[NpFigure, list[NpFigure]]:
    """
    main 的 Docstring

    :param file: 需要处理的 PSD 文件路径
    :type file: str
    :return: 包含背景图层转换后 NpFigure 对象和所有翻译图层转换后 NpFigure 对象列表的元组
    :rtype: tuple[NpFigure, list[NpFigure]]
    """
    psd = psd_tools.PSDImage.open(file)
    background_figure_list: list[NpFigure] = []
    translation_figure_list: list[NpFigure] = []
    for layer in psd:
        if layer.name == translation:
            if layer.is_group():
                for sub_layer in layer:
                    translation_figure_list.append(psd_layer_to_NpFigure(sub_layer))
            else:
                translation_figure_list.append(psd_layer_to_NpFigure(layer))
        else:
            background_figure_list.append(psd_layer_to_NpFigure(layer))

    background_figure = composite_figure(background_figure_list, psd.size)

    return background_figure, translation_figure_list
