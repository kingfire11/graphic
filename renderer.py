from PIL import Image, ImageDraw, ImageFont
from typing import Dict, List
import os
from datetime import date, timedelta
from config import STATIONS, DAYS_RU

# Цвета как на скриншоте
COLOR_HEADER_BG = (163, 194, 102)      # зелёный для дней
COLOR_STATION_BG = (255, 230, 153)     # жёлтый для станций
COLOR_CELL_BG = (255, 255, 255)        # белый для данных
COLOR_BORDER = (180, 180, 180)         # серый бордер
COLOR_TEXT = (50, 50, 50)              # тёмный текст
COLOR_HEADER_TEXT = (255, 255, 255)    # белый текст в заголовке

FONT_SIZE_HEADER = 18
FONT_SIZE_CELL = 17

COL_STATION_WIDTH = 110
COL_DAY_WIDTH = 95
ROW_HEIGHT = 42
PADDING = 8



def get_font(size: int, bold: bool = False):
    base_dir = os.path.dirname(__file__)

    # так как у тебя нет Bold — используем Italic как "выделение"
    font_name = "Sagewold-Italic.otf" if bold else "Sagewold-Regular.otf"
    font_path = os.path.join(base_dir, "fonts", font_name)

    return ImageFont.truetype(font_path, size)


def draw_cell(draw: ImageDraw, x: int, y: int, w: int, h: int,
              text: str, bg: tuple, text_color: tuple, font, bold_font=None):
    # Фон
    draw.rectangle([x, y, x + w, y + h], fill=bg, outline=COLOR_BORDER)
    # Текст по центру
    f = bold_font if bold_font else font
    bbox = draw.textbbox((0, 0), text, font=f)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = x + (w - tw) // 2
    ty = y + (h - th) // 2
    draw.text((tx, ty), text, fill=text_color, font=f)


def render_schedule_image(
    schedule: Dict[str, Dict[int, str]],
    week_start: date,
    output_path: str = "/tmp/schedule.png"
) -> str:
    """
    Рендерит таблицу расписания и сохраняет как PNG.
    Возвращает путь к файлу.
    """
    days = 7
    cols = 1 + days  # станция + 7 дней
    rows = 1 + len(STATIONS)

    img_w = COL_STATION_WIDTH + COL_DAY_WIDTH * days + 2
    img_h = ROW_HEIGHT * rows + 2

    img = Image.new("RGB", (img_w, img_h), (245, 245, 245))
    draw = ImageDraw.Draw(img)

    font = get_font(FONT_SIZE_CELL)
    bold_font = get_font(FONT_SIZE_HEADER, bold=True)

    # Заголовок: "Станция"
    draw_cell(draw, 0, 0, COL_STATION_WIDTH, ROW_HEIGHT,
              "Станция", COLOR_HEADER_BG, COLOR_HEADER_TEXT, font, bold_font)

    # Заголовки дней
    for d in range(days):
        day_date = week_start + timedelta(days=d)
        label = f"{day_date.day}.{day_date.month} {DAYS_RU[d]}"
        x = COL_STATION_WIDTH + d * COL_DAY_WIDTH
        draw_cell(draw, x, 0, COL_DAY_WIDTH, ROW_HEIGHT,
                  label, COLOR_HEADER_BG, COLOR_HEADER_TEXT, font, bold_font)

    # Строки станций
    for row_idx, station in enumerate(STATIONS):
        y = ROW_HEIGHT * (row_idx + 1)
        # Название станции
        draw_cell(draw, 0, y, COL_STATION_WIDTH, ROW_HEIGHT,
                  station, COLOR_STATION_BG, COLOR_TEXT, font, bold_font)
        # Ячейки с сотрудниками
        for d in range(days):
            x = COL_STATION_WIDTH + d * COL_DAY_WIDTH
            name = schedule.get(station, {}).get(d, "—")
            draw_cell(draw, x, y, COL_DAY_WIDTH, ROW_HEIGHT,
                      name, COLOR_CELL_BG, COLOR_TEXT, font)

    img.save(output_path)
    return output_path
