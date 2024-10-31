import torch
import numpy as np
import os
from  comfy import model_management as mm
from PIL import Image
import gc
import folder_paths
import cv2

def tensor2numpy_cv2(tensor_img):
    arr_img = tensor_img.numpy()[0] * 255
    arr_img = arr_img.astype(np.uint8)
    return arr_img
    
def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

def numpy_cv2tensor(img):
    img = img.astype(np.float32) / 255.0
    img = torch.from_numpy(img)[None,]
    return img

def get_device_by_name(device, debug: bool=False):
    """
    Args:
        "device": (["auto", "cuda", "cpu", "mps", "xpu", "meta", "directml"],{"default": "auto"}), 
    """
    if device == 'auto':
        try:
            # device = "cpu"
            # if torch.cuda.is_available():
            #     device = "cuda"
            #     # device = torch.device("cuda")
            # elif torch.backends.mps.is_available():
            #     device = "mps"
            #     # device = torch.device("mps")
            # elif torch.xpu.is_available():
            #     device = "xpu"
            #     # device = torch.device("xpu")
            device = mm.get_torch_device()
        except:
                raise AttributeError("What's your device(到底用什么设备跑的)？")
    # elif device == 'cuda':
    #     device = torch.device("cuda")
    # elif device == "mps":
    #     device = torch.device("mps")
    # elif device == "xpu":
    #     device = torch.device("xpu")
    if debug:
        print("\033[93mUse Device(使用设备):", device, "\033[0m")
    return device

def get_dtype_by_name(dtype, debug: bool=False):
    """
    "dtype": (["auto","fp16","bf16","fp32", "fp8_e4m3fn", "fp8_e4m3fnuz", "fp8_e5m2", "fp8_e5m2fnuz"],{"default":"auto"}),返回模型精度选择。
    """
    if dtype == 'auto':
        try:
            if mm.should_use_fp16():
                dtype = torch.float16
            elif mm.should_use_bf16():
                dtype = torch.bfloat16
            else:
                dtype = torch.float32
        except:
                raise AttributeError("ComfyUI version too old, can't autodetect properly. Set your dtypes manually.")
    elif dtype== "fp16":
         dtype = torch.float16
    elif dtype == "bf16":
        dtype = torch.bfloat16
    elif dtype == "fp32":
        dtype = torch.float32
    elif dtype == "fp8_e4m3fn":
        dtype = torch.float8_e4m3fn
    elif dtype == "fp8_e4m3fnuz":
        dtype = torch.float8_e4m3fnuz
    elif dtype == "fp8_e5m2":
        dtype = torch.float8_e5m2
    elif dtype == "fp8_e5m2fnuz":
        dtype = torch.float8_e5m2fnuz
    if debug:
        print("\033[93mModel Precision(模型精度):", dtype, "\033[0m")
    return dtype
        
def clean_up(debug=False):
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
    elif torch.backends.mps.is_available():
        torch.mps.empty_cache()
    elif torch.xpu.is_available():
        torch.xpu.empty_cache()
    else: 
        if debug:
            print('\033[93m', 'Not needed', '\033[0m')
        pass

def get_files_with_extension(folder_name, extension=['.safetensors']):
    """_summary_

    Args:
        folder_name (_type_): models根目录下的文件夹，不能指向更深的子目录。
        extension (list, optional): 要获取的文件的后缀。

    Returns:
        _type_: _description_
    """
    try:
        folders = folder_paths.get_folder_paths(folder_name)
    except:
        folders = []

    if not folders:
        folders = [os.path.join(folder_paths.models_dir, folder_name)]
    if not os.path.isdir(folders[0]):
        folders = [os.path.join(folder_paths.base_path, folder_name)]
    if not os.path.isdir(folders[0]):
        return {}
    
    filtered_folders = []
    for x in folders:
        if not os.path.isdir(x):
            continue
        the_same = False
        for y in filtered_folders:
            if os.path.samefile(x, y):
                the_same = True
                break
        if not the_same:
            filtered_folders.append(x)

    if not filtered_folders:
        return {}

    output = {}
    for x in filtered_folders:
        files, folders_all = folder_paths.recursive_search(x, excluded_dir_names=[".git"])
        filtered_files = folder_paths.filter_files_extensions(files, extension)

        for f in filtered_files:
            output[f] = x

    return output

def download_singlefile_from_huggingface(repo_id, file_name, root_folder=None, new_name=None, revision="main"):
    """_summary_

    Args:
        function: 从huggingface下载单个文件到指定文件夹或者.cache，无需提前创建根目录文件夹
        repo_id (_type_): repoid,例如模型地址https://huggingface.co/Kijai/depth-fm-pruned，那么repoid就是Kijai/depth-fm-pruned
        file_name (_type_): 要下载的文件名字，包含后缀
        root_folder (_type_): 下载到哪个目录下，如果为None，则缓存到.cache
        new_name (_type_, optional): 是否要重命名，如果重命名，这个就是新名字，包含后缀
        revision: 分支
    """
    from huggingface_hub import hf_hub_download
    hf_hub_download(repo_id, file_name, local_dir=root_folder, revision=revision)
    if new_name != None and root_folder != None:
        old_file_name = os.path.join(root_folder, file_name)
        new_file_name = os.path.join(root_folder, new_name)
        os.rename(old_file_name, new_file_name)

def download_repoid_model_from_huggingface(repo_id: str, Base_Path: str, ignore_patterns: list = None, resume_download: bool=False):
    """_summary_

    Args:
        function: 根据提供的repo名字下载文件夹模型内全部文件到指定的模型目录(非.cache)，无需提前创建目录，纯离线。
        repo_id (str): 模型ID，作者名字+模型名字,repo_id，例如模型网址https://huggingface.co/ZhengPeng7/BiRefNet_lite，那么repo_id就是ZhengPeng7/BiRefNet_lite。
        Base_Path (str): 下载到本地指定目录(非根目录，要模型文件夹目录)(例如D:\AI\ComfyUI_windows_portable\ComfyUI\models\rembg\models--ZhengPeng7--BiRefNet_lite)。
        local_dir_use_symlinks:是否使用blob编码存放，这种存放方式，第一次执行加载时会需要全球网络连接huggingface查找更新。
        ignore_patterns: ["*x*"(指定文件夹), "*.x"(指定后缀的文件)]不下载某些文件，例如snapshot_download(repo_id="lemonaddie/geowizard", ignore_patterns=["*vae*", "*.ckpt", "*.pt", "*.png", "*non_ema*", "*safety_checker*", "*.bin"], 忽略下载safety_checker、vae和safety_checker整个文件夹、以及其他后缀的文件.ckpt---.pt---.png---.bin。
    Returns:
        无
    """
    from huggingface_hub import snapshot_download as hg_snapshot_download
    hg_snapshot_download(repo_id, 
                        local_dir=Base_Path, 
                        ignore_patterns=ignore_patterns, 
                        local_dir_use_symlinks=False,
                        resume_download=resume_download, 
                    )

Pillow_Color_Names = [
    "red",
    "green",
    "blue",
    "white",
    "black",
    "yellow",
    "pink",
    "gold",
    "purple",
    "brown",
    "orange",
    "tomato",
    "violet",
    "wheat",
    "snow",
    "yellowgreen",
    "gray",
    "grey",
    "aliceblue",
    "antiquewhite",
    "aqua",
    "aquamarine",
    "azure",
    "beige",
    "bisque",
    "blanchedalmond",
    "blueviolet",
    "burlywood",
    "cadetblue",
    "chartreuse",
    "chocolate",
    "coral",
    "cornflowerblue",
    "cornsilk",
    "crimson",
    "cyan",
    "darkblue",
    "darkcyan",
    "darkgoldenrod",
    "darkgray",
    "darkgrey",
    "darkgreen",
    "darkkhaki",
    "darkmagenta",
    "darkolivegreen",
    "darkorange",
    "darkorchid",
    "darkred",
    "darksalmon",
    "darkseagreen",
    "darkslateblue",
    "darkslategray",
    "darkslategrey",
    "darkturquoise",
    "darkviolet",
    "deeppink",
    "deepskyblue",
    "dimgray",
    "dimgrey",
    "dodgerblue",
    "firebrick",
    "floralwhite",
    "forestgreen",
    "fuchsia",
    "gainsboro",
    "ghostwhite",
    "goldenrod",
    "greenyellow",
    "honeydew",
    "hotpink",
    "indianred",
    "indigo",
    "ivory",
    "khaki",
    "lavender",
    "lavenderblush",
    "lawngreen",
    "lemonchiffon",
    "lightblue",
    "lightcoral",
    "lightcyan",
    "lightgoldenrodyellow",
    "lightgreen",
    "lightgray",
    "lightgrey",
    "lightpink",
    "lightsalmon",
    "lightseagreen",
    "lightskyblue",
    "lightslategray",
    "lightslategrey",
    "lightsteelblue",
    "lightyellow",
    "lime",
    "limegreen",
    "linen",
    "magenta",
    "maroon",
    "mediumaquamarine",
    "mediumblue",
    "mediumorchid",
    "mediumpurple",
    "mediumseagreen",
    "mediumslateblue",
    "mediumspringgreen",
    "mediumturquoise",
    "mediumvioletred",
    "midnightblue",
    "mintcream",
    "mistyrose",
    "moccasin",
    "navajowhite",
    "navy",
    "oldlace",
    "olive",
    "olivedrab",
    "orangered",
    "orchid",
    "palegoldenrod",
    "palegreen",
    "paleturquoise",
    "palevioletred",
    "papayawhip",
    "peachpuff",
    "peru",
    "plum",
    "powderblue",
    "rebeccapurple",
    "rosybrown",
    "royalblue",
    "saddlebrown",
    "salmon",
    "sandybrown",
    "seagreen",
    "seashell",
    "sienna",
    "silver",
    "skyblue",
    "slateblue",
    "slategray",
    "slategrey",
    "springgreen",
    "steelblue",
    "tan",
    "teal",
    "thistle",
    "turquoise",
    "whitesmoke",
    ]

def cv2img_canny(img, low_threshold=64, high_threshold=100):
    """_summary_

    Args:
        img (_type_): 输入cv2_numpy类型图片，从tensor转换需要numpy_cv2tensor
        low_threshold (int, optional): _description_. Defaults to 64.
        high_threshold (int, optional): _description_. Defaults to 100.

    Returns:
        _type_: 输出pillow(np.array)类型图片，转换成tensor需要pil2tensor
    """
    # low_threshold = 64
    # high_threshold = 100
    img = cv2.Canny(img, low_threshold, high_threshold)
    img = img[:, :, None]
    img = np.concatenate([img, img, img], axis=2)
    return Image.fromarray(img)