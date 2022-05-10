import sys
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QGridLayout
from realUI_b import *
import cv2
import matplotlib
import numpy as np

matplotlib.use("Qt5Agg")  # 声明使用QT5
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

TIMEWINDOW = 1000
SLIDEWINDOW = TIMEWINDOW / 2


class MyFigure(FigureCanvas):
    def __init__(self, width, height, dpi):
        # 创建一个Figure,该Figure为matplotlib下的Figure，不是matplotlib.pyplot下面的Figure
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        # 在父类中激活Figure窗口，此句必不可少，否则不能显示图形
        super(MyFigure, self).__init__(self.fig)
        # 调用Figure下面的add_subplot方法，类似于matplotlib.pyplot下面的subplot(1,1,1)方法
        self.axes = self.fig.add_subplot(111)


class MainWindow(QMainWindow, Ui_Mwbreath):  # 多重继承QMainWindow和Ui_MainWindow
    def __init__(self):
        super(MainWindow, self).__init__()  # 先调用父类QMainWindow的初始化方法
        self.setupUi(self)  # 再调用setupUi方法
        # cv显示参数
        self.timer_camera = QtCore.QTimer()  # 定义定时器，用于控制显示视频的帧率
        self.cap = cv2.VideoCapture()  # 视频流
        self.CAM_NUM = 0  # 为0时表示视频流来自笔记本内置摄像头
        # wave显示参数
        self.timer_waver = QtCore.QTimer()  # 定义定时器，用于控制显示帧率
        self.F = MyFigure(width=3, height=2, dpi=100)

    def on_ab(self):
        QMessageBox.information(self, 'about us', '北京邮电大学先进网络实验室Wi-Fi感知小组成果。\n感谢深圳信息通信研究所大力支持。')

    def on_hb(self):
        QMessageBox.information(self, 'help', '目前版本仅为演示demo。\n如果遇到bug建议重新启动。')

    def on_cv(self):
        if self.timer_camera.isActive() == False:  # 若定时器未启动
            flag = self.cap.open(self.CAM_NUM)  # 参数是0，表示打开笔记本的内置摄像头，参数是视频文件路径则打开视频
            if flag == False:  # flag表示open()成不成功
                msg = QtWidgets.QMessageBox.warning(self, 'warning', "请检查相机于电脑是否连接正确", buttons=QtWidgets.QMessageBox.Ok)
            else:
                self.timer_camera.start(30)  # 定时器开始计时30ms，结果是每过30ms从摄像头中取一帧显示
                self.onbutton.setText('off')
                self.timer_camera.timeout.connect(self.show_camera)
        else:
            self.timer_camera.stop()  # 关闭定时器
            self.cap.release()  # 释放视频流
            self.cvUI.clear()  # 清空视频显示区域
            self.onbutton.setText('on')

    def show_camera(self):
        flag, self.image = self.cap.read()  # 从视频流中读取
        show = cv2.resize(self.image, (500, 380))  # 把读到的帧的大小重新设置
        show = cv2.cvtColor(show, cv2.COLOR_BGR2RGB)  # 视频色彩转换回RGB，这样才是现实的颜色
        showImage = QtGui.QImage(show.data, show.shape[1], show.shape[0],
                                 QtGui.QImage.Format_RGB888)  # 把读取到的视频数据变成QImage形式
        self.cvUI.setPixmap(QtGui.QPixmap.fromImage(showImage))  # 往显示视频的Label里 显示QImage

    def on_wave(self):
        if self.timer_waver.isActive() == False:  # 若定时器未启动
            self.timer_waver.start(1000)  # 定时器开始计时，结果是每1000ms从摄像头中取一帧显示
            # 画图
            self.timer_waver.timeout.connect(self.plotxy)
            # 其他显示设置
            self.wavetext.raise_()
            self.on2button.setText('off')
        else:
            self.waveUI.clear()

    def plotxy(self):
        # 更新figure
        self.F.fig.suptitle("cos")
        t = np.arange(0.0, 5.0, 0.01)
        self.F.axes.plot(t, np.cos(2 * np.pi * t))
        # 设置布局
        self.gridlayout = QGridLayout(self.waveUI)
        self.gridlayout.addWidget(self.F)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('image/favicon.ico'))  # 加载 icon
    ui = MainWindow()
    ui.show()
    sys.exit(app.exec_())
