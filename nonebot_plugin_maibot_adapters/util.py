import base64
from pathlib import Path
import hashlib

def local_file_to_base64(file_path: str) -> str:
    # 读取本地图片文件
    with open(file_path, "rb") as f:
        image_data = f.read()
    
    # 拼接Base64字符串
    base64_str = base64.b64encode(image_data).decode("utf-8")
    return base64_str

def detect_image_type(data: bytes) -> str:
    """通过文件头识别常见图片格式"""
    if len(data) < 12:
        return "unknown"
    
    # 常见图片格式的魔数检测
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return "png"
    elif data.startswith(b'\xff\xd8'):
        return "jpeg"
    elif data[:6] in (b'GIF87a', b'GIF89a'):
        return "gif"
    elif data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return "webp"
    elif data.startswith(b'\x00\x00\x01\x00'):
        return "ico"
    elif data.startswith(b'BM'):
        return "bmp"
    else:
        return "unknown"

def base64_to_image(base64_str: str, save_dir: str = "data/images") -> str:
    """处理无头Base64字符串并保存为哈希命名的图片"""
    try:
        # 解码Base64
        image_data = base64.b64decode(base64_str)
        
        # 计算哈希值
        file_hash = hashlib.md5(image_data).hexdigest()
        
        # 检测图片类型
        image_type = detect_image_type(image_data)
        
        # 映射类型到扩展名
        type_mapping = {
            "png": "png",
            "jpeg": "jpg",
            "gif": "gif",
            "webp": "webp",
            "ico": "ico",
            "bmp": "bmp",
            "unknown": "png"  # 未知类型默认png
        }
        file_ext = type_mapping[image_type]
        
        # 构建保存路径
        save_path = Path("data/images").resolve() / f"{file_hash}.{file_ext}"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 仅当文件不存在时保存
        if not save_path.exists():
            with open(save_path, "wb") as f:
                f.write(image_data)
        
        return f"file:///{save_path.absolute().as_posix()}"
    except Exception as e:
        raise ValueError(f"Base64解码失败: {str(e)}")