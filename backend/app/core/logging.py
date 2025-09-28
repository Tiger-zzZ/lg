import structlog
import logging.config
import os
from datetime import datetime
from pathlib import Path
from app.core.config import settings


def setup_logging():
    """配置结构化日志"""

    # 根据环境设置日志级别
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # 创建日志目录
    log_dir = Path("/app/app/log")
    log_dir.mkdir(exist_ok=True)

    # 生成日志文件名（按日期）
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"lg-backend-{today}.log"
    error_log_file = log_dir / f"lg-backend-error-{today}.log"

    # 详细的格式化器
    detailed_formatter = {
        "format": "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s - %(pathname)s:%(lineno)d"
    }

    json_formatter = {
        "()": structlog.stdlib.ProcessorFormatter,
        "processor": structlog.dev.ConsoleRenderer(colors=True),
    }

    # 配置标准logging
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": detailed_formatter,
            "json": json_formatter,
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "level": log_level,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(log_file),
                "formatter": "detailed",
                "level": log_level,
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(error_log_file),
                "formatter": "detailed",
                "level": "ERROR",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8",
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console", "file", "error_file"],
        },
        "loggers": {
            "app": {
                "level": "DEBUG" if settings.DEBUG else log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "DEBUG" if settings.DEBUG else log_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO" if settings.DEBUG else "WARNING",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "DEBUG" if settings.DEBUG else "WARNING",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "sqlalchemy.pool": {
                "level": "DEBUG" if settings.DEBUG else "WARNING",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "fastapi": {
                "level": "DEBUG" if settings.DEBUG else "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "httpx": {
                "level": "DEBUG" if settings.DEBUG else "WARNING",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "chromadb": {
                "level": "DEBUG" if settings.DEBUG else "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
        }
    })

    # 配置structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.CallsiteParameterAdder(
                parameters=[structlog.processors.CallsiteParameter.FILENAME,
                           structlog.processors.CallsiteParameter.LINENO]
            ),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 输出日志配置信息
    logger = structlog.get_logger("app.core.logging")
    logger.info("日志系统已配置",
                log_level=settings.LOG_LEVEL,
                debug_mode=settings.DEBUG,
                log_file=str(log_file),
                error_log_file=str(error_log_file))


# 获取logger实例
logger = structlog.get_logger(__name__)