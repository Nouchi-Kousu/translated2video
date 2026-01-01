# [Translated2Video](https://github.com/Nouchi-Kousu/translated2video)

用于半自动将完成嵌字的PSD文件转换为带导读视频的工具。

> 视频样式参见[示例视频](https://www.bilibili.com/video/BV1oxiGBSExm)

项目由两部分组成：
- [Translated2Figure](https://github.com/Nouchi-Kousu/translated2video/blob/main/translated2figure.jsx): Photoshop脚本，用于在Photoshop中批量处理PSD文件，输出逐图层PNG文件,
- [Translated2Video](https://pypi.org/project/translated2video): Python脚本，用于将PNG文件转换为视频文件。

## 使用方法

### Translated2Figure

使用Photoshop打开需要处理的PSD文件，运行[`translated2figure.jsx`](https://github.com/Nouchi-Kousu/translated2video/blob/main/translated2figure.jsx)脚本。
使用前需在当前工作目录下创建与PSD文件同名的文件夹，并将每个图层导出为PNG文件，保存在对应的文件夹中。

当安装Translated2Figure后，会注册命令行工具`t2f`，在命令行中运行`t2f`（无参数）可为当前工作目录下的PSD文件批量生成同名文件夹。

#### PSD文件要求

- 每个PSD文件中必须包含一个名为“翻译”或“translation”的图层组（以下均用“翻译”代指），该图层组中用于存放所有需要导出的翻译图层。
- 当隐藏“翻译”图层组并显示其余所有图层时，应为完整无字背景，即视频背景。
- “翻译”图层组中可以有子组，子组将被视为整体导出。
- “翻译”图层组中的图层或子组应按从下到上的顺序排列，导出时将依次编号。
- 由于使用Opencv处理图片和视频，由于最终视频名来自PSD文件名，请避免使用非ASCII字符（如中文）作为PSD文件名，或将导出图片后的文件夹名改为纯ASCII字符。

> 示例PSD文件可自[Releases](https://github.com/Nouchi-Kousu/translated2video/releases)下载

### Translated2Video

建议使用uv tool安装工具：
```bash
uv tool install translated2video
```
这将在系统中注册命令行工具`t2v`和`t2f`。

> 如何安装uv请参见[uv官方文档](https://docs.astral.sh/uv/)。

在命令行中运行`t2v`，将当前工作目录下的所有文件夹中的PNG文件转换为视频文件，并在当前目录下输出为以父文件夹名称命名的MP4文件。
```bash
t2v [OPTIONS]
```

所有参数均为可选：
- `--rate`, `-r`: 设置输出视频的帧率，默认为24。
- `--interval`, `-i`: 设置每张图片在视频中持续的时间，单位为秒，默认为10秒。
- `--transit`, `-t`: 设置图片之间的过渡时间，单位为毫秒，默认为500毫秒。
- `--width`, `-w`: 设置输出视频的宽度，默认为-1，表示自动计算宽度以保持原始图片的宽高比。
- `--height`, `-h`: 设置输出视频的高度，默认为-1，表示自动计算高度以保持原始图片的宽高比。
- `--help`: 显示帮助信息。

