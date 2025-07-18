import os
import sys
from loguru import logger
from config.config_loader import load_config
from config.settings import check_config_file
from datetime import datetime

SERVER_VERSION = "0.6.1"
_logger_initialized = False


def get_module_abbreviation(module_name, module_dict):
    """获取模块名称的缩写，如果为空则返回00
    如果名称中包含下划线，则返回下划线后面的前两个字符
    """
    module_value = module_dict.get(module_name, "")
    if not module_value:
        return "00"
    if "_" in module_value:
        parts = module_value.split("_")
        return parts[-1][:2] if parts[-1] else "00"
    return module_value[:2]


def build_module_string(selected_module):
    """构建模块字符串"""
    return (
        get_module_abbreviation("VAD", selected_module)
        + get_module_abbreviation("ASR", selected_module)
        + get_module_abbreviation("LLM", selected_module)
        + get_module_abbreviation("TTS", selected_module)
        + get_module_abbreviation("Memory", selected_module)
        + get_module_abbreviation("Intent", selected_module)
    )


def formatter(record):
    """为没有 tag 的日志添加默认值"""
    record["extra"].setdefault("tag", record["name"])
    return record["message"]


def setup_logging():
    check_config_file()
    """从配置文件中读取日志配置，并设置日志输出格式和级别"""
    config = load_config()
    log_config = config["log"]
    global _logger_initialized

    # 第一次初始化时配置日志
    if not _logger_initialized:
        logger.configure(
            extra={
                "selected_module": log_config.get("selected_module", "00000000000000")
            }
        )  # 新增配置
        log_format = log_config.get(
            "log_format",
            "<green>{time:YYMMDD HH:mm:ss}</green>[{version}_{extra[selected_module]}][<light-blue>{extra[tag]}</light-blue>]-<level>{level}</level>-<light-green>{message}</light-green>",
        )
        log_format_file = log_config.get(
            "log_format_file",
            "{time:YYYY-MM-DD HH:mm:ss} - {version}_{extra[selected_module]} - {name} - {level} - {extra[tag]} - {message}",
        )
        selected_module_str = logger._core.extra["selected_module"]

        log_format = log_format.replace("{version}", SERVER_VERSION)
        log_format = log_format.replace("{selected_module}", selected_module_str)
        log_format_file = log_format_file.replace("{version}", SERVER_VERSION)
        log_format_file = log_format_file.replace(
            "{selected_module}", selected_module_str
        )

        log_level = log_config.get("log_level", "INFO")
        log_dir = log_config.get("log_dir", "tmp")
        log_file = log_config.get("log_file", "server.log")
        data_dir = log_config.get("data_dir", "data")

        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)

        # 配置日志输出
        logger.remove()

        # 输出到控制台
        logger.add(sys.stdout, format=log_format, level=log_level, filter=formatter)

        # 输出到文件 - 统一目录，按大小轮转
        # 日志文件完整路径
        log_file_path = os.path.join(log_dir, log_file)

        # 添加日志处理器
        logger.add(
            log_file_path,
            format=log_format_file,
            level=log_level,
            filter=formatter,
            rotation="10 MB",  # 每个文件最大10MB
            retention="30 days",  # 保留30天
            compression=None,
            encoding="utf-8",
            enqueue=True,  # 异步安全
            backtrace=True,
            diagnose=True,
        )
        _logger_initialized = True  # 标记为已初始化

    return logger


def update_module_string(selected_module_str):
    """更新模块字符串并重新配置日志处理器"""
    logger.debug(f"更新日志配置组件")
    current_module = logger._core.extra["selected_module"]

    if current_module == selected_module_str:
        logger.debug(f"组件未更改无需更新")
        return

    try:
        logger.configure(extra={"selected_module": selected_module_str})

        config = load_config()
        log_config = config["log"]

        log_format = log_config.get(
            "log_format",
            "<green>{time:YYMMDD HH:mm:ss}</green>[{version}_{extra[selected_module]}][<light-blue>{extra[tag]}</light-blue>]-<level>{level}</level>-<light-green>{message}</light-green>",
        )
        log_format_file = log_config.get(
            "log_format_file",
            "{time:YYYY-MM-DD HH:mm:ss} - {version}_{extra[selected_module]} - {name} - {level} - {extra[tag]} - {message}",
        )

        log_format = log_format.replace("{version}", SERVER_VERSION)
        log_format = log_format.replace("{selected_module}", selected_module_str)
        log_format_file = log_format_file.replace("{version}", SERVER_VERSION)
        log_format_file = log_format_file.replace(
            "{selected_module}", selected_module_str
        )

        logger.remove()
        logger.add(
            sys.stdout,
            format=log_format,
            level=log_config.get("log_level", "INFO"),
            filter=formatter,
        )

        # 更新文件日志配置 - 统一目录，按大小轮转
        log_dir = log_config.get("log_dir", "tmp")
        log_file = log_config.get("log_file", "server.log")

        # 日志文件完整路径
        log_file_path = os.path.join(log_dir, log_file)

        logger.add(
            log_file_path,
            format=log_format_file,
            level=log_config.get("log_level", "INFO"),
            filter=formatter,
            rotation="10 MB",  # 每个文件最大10MB
            retention="30 days",  # 保留30天
            compression=None,
            encoding="utf-8",
            enqueue=True,  # 异步安全
            backtrace=True,
            diagnose=True,
        )

    except Exception as e:
        logger.error(f"日志配置更新失败: {str(e)}")
        raise
