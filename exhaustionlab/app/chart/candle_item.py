# Lightweight candlestick renderer for PyQtGraph
import pyqtgraph as pg
from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter


class CandlestickItem(pg.GraphicsObject):
    def __init__(self, df):
        super().__init__()
        self._df = df  # DataFrame with columns: ts_open, open, high, low, close, volume
        self.generatePicture()

    def generatePicture(self):
        self.picture = pg.QtGui.QPicture()
        p = QPainter(self.picture)
        w = 0.6  # candle body width (in x axis units)
        for i, row in enumerate(self._df.itertuples()):
            open_price, high_price, low_price, close_price = row.open, row.high, row.low, row.close
            candle_color = pg.mkColor(0, 170, 0) if close_price >= open_price else pg.mkColor(200, 30, 30)
            p.setPen(pg.mkPen(candle_color))
            p.setBrush(pg.mkBrush(candle_color))
            # wick
            p.drawLine(pg.QtCore.QPointF(i, high_price), pg.QtCore.QPointF(i, low_price))
            # body
            body_height = abs(close_price - open_price)
            rect = QRectF(
                i - w / 2,
                min(open_price, close_price),
                w,
                body_height if body_height > 1e-12 else 0.0000001,
            )
            p.drawRect(rect)
        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return self.picture.boundingRect()

    def update_data(self, df):
        self._df = df
        self.generatePicture()
        self.update()
