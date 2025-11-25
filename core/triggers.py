# file: core/triggers.py

import logging
from PySide6.QtCore import QObject, Signal
from pynput import keyboard

logger = logging.getLogger(__name__)

class BluetoothTrigger(QObject):
    # Tách thành 2 tín hiệu riêng biệt
    triggered_1 = Signal() # Tín hiệu cho Camera 1 (Volume Up)
    triggered_2 = Signal() # Tín hiệu cho Camera 2 (Volume Down)

    def __init__(self):
        super().__init__()
        self.key_1 = keyboard.Key.media_volume_up
        self.key_2 = keyboard.Key.media_volume_down
        self.listener = None
        
        # Dùng Set để lưu các phím đang được giữ (tránh spam tín hiệu khi đè phím)
        self._pressed_keys = set()
        self.is_active = False 

    def on_press(self, key):
        # Chỉ xử lý khi active
        if self.is_active:
            # Logic cho Camera 1
            if key == self.key_1 and key not in self._pressed_keys:
                self._pressed_keys.add(key)
                logger.info(f"Phát hiện Trigger 1 (Vol Up)")
                self.triggered_1.emit()
            
            # Logic cho Camera 2
            elif key == self.key_2 and key not in self._pressed_keys:
                self._pressed_keys.add(key)
                logger.info(f"Phát hiện Trigger 2 (Vol Down)")
                self.triggered_2.emit()

    def on_release(self, key):
        # Xóa phím khỏi danh sách đã nhấn để cho phép nhấn lần tiếp theo
        if key in self._pressed_keys:
            self._pressed_keys.remove(key)

    def activate(self):
        """Bật chức năng lắng nghe."""
        logger.info("Trigger đã được BẬT.")
        self.is_active = True

    def deactivate(self):
        """Tắt chức năng lắng nghe."""
        logger.info("Trigger đã được TẮT.")
        self.is_active = False
        self._pressed_keys.clear()

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