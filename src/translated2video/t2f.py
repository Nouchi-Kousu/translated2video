import os


def main():
    """
    为当前目录下的所有PSD文件创建同名文件夹。"""
    psd_list = [f for f in os.listdir(os.getcwd()) if f.endswith(".psd")]
    psd_name_list = [os.path.splitext(f)[0] for f in psd_list]
    for psd_name in psd_name_list:
        os.mkdir(psd_name)