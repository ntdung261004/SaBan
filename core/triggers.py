# Thay thế TOÀN BỘ file core/triggers.py

import logging
from PySide6.QtCore import QObject, Signal
from pynput import keyboard

logger = logging.getLogger(__name__)

class BluetoothTrigger(QObject):
    triggered = Signal()

    def __init__(self):
        super().__init__()
        self.trigger_key = keyboard.Key.media_volume_up
        self.listener = None
        self._is_key_pressed = False
        self.is_active = False # Cờ trạng thái để bật/tắt chức năng

    def on_press(self, key):
        # Chỉ gửi tín hiệu khi đang ở trạng thái active
        if self.is_active and key == self.trigger_key and not self._is_key_pressed:
            self._is_key_pressed = True
            logger.info(f"Phát hiện tín hiệu trigger từ phím: {key}")
            self.triggered.emit()

    def on_release(self, key):
        if key == self.trigger_key:
            self._is_key_pressed = False

    def activate(self):
        """Bật chức năng lắng nghe."""
        logger.info("Trigger đã được BẬT.")
        self.is_active = True

    def deactivate(self):
        """Tắt chức năng lắng nghe."""
        logger.info("Trigger đã được TẮT.")
        self.is_active = False

    def start_global_listener(self):
        """Khởi động luồng lắng nghe một lần duy nhất."""
        if self.listener is None:
            self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
            self.listener.start()
            logger.info(f"Luồng lắng nghe phím bấm toàn cục đã bắt đầu.")

    def stop_global_listener(self):
        """Dừng luồng lắng nghe khi thoát ứng dụng."""
        if self.listener is not None:
            self.listener.stop()
            self.listener.join()
            self.listener = None
            logger.info("Luồng lắng nghe phím bấm toàn cục đã dừng.")