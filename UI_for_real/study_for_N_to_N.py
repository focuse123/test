# 信号触发信号\信号触发槽函数
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *


class SinClass(QObject):
    ##声明一个无参数的信号
    sin1 = pyqtSignal()

    ##声明带一个int类型参数的信号
    sin2 = pyqtSignal(int)

    def __init__(self, parent=None):
        super(SinClass, self).__init__(parent)

        # 信号sin1触发sin1Call和sin2Call这两个槽函数
        self.sin1.connect(self.sin1Call)
        self.sin1.connect(self.sin2Call)

        # 信号sin2触发信号sin1
        self.sin2.connect(self.sin1)

        # 信号发射
        self.sin1.emit()
        self.sin2.emit(1)

        # 断开sin1、sin2信号与各槽的连接
        self.sin1.disconnect(self.sin1Call)
        self.sin1.disconnect(self.sin2Call)
        self.sin2.disconnect(self.sin1)
        #
        # 信号sin1和sin2连接同一个槽sin1Call
        self.sin1.connect(self.sin1Call)
        self.sin2.connect(self.sin1Call)
        #
        # 信号再次发射
        self.sin1.emit()
        self.sin2.emit(1)

    def sin1Call(self):
        print("sin1 emit")

    def sin2Call(self):
        print("sin2 emit")


sin = SinClass()