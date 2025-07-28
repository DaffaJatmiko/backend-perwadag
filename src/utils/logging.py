"""Logging configuration utilities."""

import logging
import logging.handlers
import json
import os
from datetime import datetime

from src.core.config import settings


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, service_name):
        super().__init__()
        self.service_name = service_name

    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if record.exc_info:
            log_entry['exc_info'] = self.formatException(record.exc_info)
        if record.stack_info:
            log_entry['stack_info'] = self.formatStack(record.stack_info)
            
        return json.dumps(log_entry)


def setup_logging():
    """Setup application logging."""
    import logging.config
    
    # Create logs directory with full path
    log_directory = os.path.abspath(settings.LOG_DIRECTORY)
    print(f"DEBUG: LOG_DIRECTORY setting: {settings.LOG_DIRECTORY}")
    print(f"DEBUG: Resolved log directory: {log_directory}")
    print(f"DEBUG: Current working directory: {os.getcwd()}")
    
    try:
        os.makedirs(log_directory, exist_ok=True)
        print(f"DEBUG: Successfully created directory: {log_directory}")
        
        # Test write permissions
        test_file = os.path.join(log_directory, 'test_write.tmp')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        print(f"DEBUG: Write test successful in: {log_directory}")
    except (OSError, PermissionError) as e:
        print(f"Error with log directory {log_directory}: {e}")
        print("Falling back to console-only logging")
        # Fallback to console-only logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        return

    log_file_path = os.path.join(log_directory, f'{settings.SERVICE_NAME}.log')
    
    # Logging configuration
    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': 'src.utils.logging.JSONFormatter',
                'service_name': settings.SERVICE_NAME,
            },
            'simple': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'simple',
                'stream': 'ext://sys.stdout',
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'json',
                'filename': log_file_path,
                'maxBytes': settings.LOG_MAX_BYTES,
                'backupCount': settings.LOG_BACKUP_COUNT,
                'encoding': 'utf-8',
            },
        },
        'loggers': {
            '': {  # Root logger
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False,
            },
            'uvicorn': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False,
            },
            'uvicorn.access': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False,
            },
        },
    }
    
    try:
        # Test if log file can be created first
        test_log_file = os.path.join(log_directory, 'test_handler.log')
        handler = logging.handlers.RotatingFileHandler(
            test_log_file, 
            maxBytes=settings.LOG_MAX_BYTES,
            backupCount=settings.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        handler.close()
        os.remove(test_log_file)
        print(f"DEBUG: Handler test successful")
        
        logging.config.dictConfig(LOGGING_CONFIG)
        print(f"DEBUG: Logging configuration applied successfully")
    except Exception as e:
        print(f"Error setting up logging configuration: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        # Fallback to console-only logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )