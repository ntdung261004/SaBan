# file: utils/audio.py
# NỘI DUNG ĐÃ ĐƯỢC RÚT GỌN CHỈ GIỮ LẠI ÂM THANH "SHOT"

import logging
import os
import pygame
from utils.resource_path import resource_path

logger = logging.getLogger(__name__)

class AudioManager:
    """
    Lớp quản lý âm thanh sử dụng pygame.mixer.
    """
    def __init__(self):
        try:
            pygame.mixer.init()
            self.sounds = {}
            logger.info("Pygame mixer đã được khởi tạo thành công.")
            self._load_sounds()
        except pygame.error as e:
            logger.error(f"Lỗi khi khởi tạo pygame.mixer: {e}. Âm thanh sẽ không hoạt động.")
            self.sounds = None

    def _load_sounds(self):
        """Tải duy nhất file âm thanh shot.mp3."""
        if self.sounds is None: return
        logger.info("Đang tải file âm thanh 'shot'...")
        
        sounds_dir = resource_path(os.path.join("assets", "sounds"))

        # <<< SỬA LỖI: Chỉ định nghĩa âm thanh 'shot' cần tải
        sound_name = 'shot'
        sound_path = os.path.join(sounds_dir, f"{sound_name}.mp3")
        
        if os.path.exists(sound_path):
            try:
                self.sounds[sound_name] = pygame.mixer.Sound(sound_path)
            except pygame.error as e:
                logger.error(f"Lỗi khi tải file âm thanh '{sound_name}': {e}")
        else:
            logger.warning(f"Không tìm thấy file âm thanh: {sound_path}")

    def play_sound(self, name: str):
        """Phát một âm thanh đã được tải dựa theo tên."""
        if self.sounds and name in self.sounds:
            self.sounds[name].play()
        elif self.sounds is None:
            logger.warning("Không thể phát âm thanh vì pygame.mixer chưa được khởi tạo.")
        else:
            logger.warning(f"Không tìm thấy âm thanh có tên: '{name}'")
            
    # <<< SỬA LỖI: Đã xóa toàn bộ phương thức play_score không cần thiết