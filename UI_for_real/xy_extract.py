from read_BF_file import *
from scipy.signal import savgol_filter
from sklearn.decomposition import PCA
import numpy.fft as fft
from scipy.signal import find_peaks
import statsmodels.api as sm


def rid_nan(ret):
    for fi in range(30):
        aa = ret[fi, :]
        for i in range(len(aa)):
            if np.isnan(aa[i]) or np.isinf(aa[i]):
                aa[i] = aa[i - 1]
        ret[fi, :] = aa
    return ret


def csi_radio(radio):
    an1 = radio[0, :, :]
    an2 = radio[1, :, :]
    an3 = radio[2, :, :]
    ret1 = rid_nan(np.divide(an1, an2))
    ret2 = rid_nan(np.divide(an2, an3))
    radio = np.array([ret1, ret2])
    # print('csi_radio中CSI商：', radio.shape)
    return radio


def savgol(SCret, wid=255):
    # x = savgol_filter(np.real(SCret), wid, 3)
    # y = savgol_filter(np.imag(SCret), wid, 3)
    try:
        phase = savgol_filter(np.angle(SCret), wid, 3)
        ampitude = savgol_filter(np.abs(SCret), wid, 3)
        SCret = ampitude * np.exp(1j * phase)
        x = np.real(SCret)
        y = np.imag(SCret)
    except (ValueError, np.linalg.LinAlgError):
        x = np.real(SCret)
        y = np.imag(SCret)
    return x, y


def binRemove(BNR, sequence, k=1):
    '''
    :param sequence: np.array (a,)
    :return: sequence: np.array (≤a,)    index  ((left < ta) & (ta < right))
    '''
    percentile = np.percentile(sequence, (25, 50, 75), interpolation='midpoint')
    Q1 = percentile[0]  # 上四分位数
    Q3 = percentile[2]  # 下四分位数
    IQR = Q3 - Q1  # 四分位距
    rt = Q3 + k * IQR  # 上限 非异常范围内的最大值
    lt = Q1 - k * IQR  # 下限 非异常范围内的最小值
    idx = (lt < sequence) & (sequence < rt)

    idxx = (lt > sequence) & (sequence > rt)
    BNR[idxx] = 0
    return BNR, idx


def getBNR(oz, fs):
    lo = len(oz)  # 采样点数
    N = 8192  # FFT点数
    S = np.pad(oz, (0, N - lo))  # 零填充
    complex_array = fft.fft(S)

    # 得到分解波的频率序列
    freqs = fft.fftfreq(N, 1 / fs)
    # 复数的模为信号的振幅(能量大小)
    pows = np.abs(complex_array)

    # 仅保留正的部分
    pows = pows[freqs >= 0]
    freqs = freqs[freqs >= 0]
    idx = (freqs > 11 / 60) & (freqs < 37 / 60)

    # 人类正常呼吸范围(17bpm到37bpm)对应频率17/60~37/60Hz占总能量的比
    pow = np.sum(pows)
    rpow = np.sum(pows[idx])
    BNR = rpow / pow
    return BNR


def PCAozandBNR(a, b, fs=100):
    # a、b分别表示CSI_ret序列的实部和虚部，fs为发包速率100

    # 利用PCA获得投影
    l = np.array([a, b]).T
    pca = PCA(n_components='mle')
    pca.fit(l)
    oz = pca.transform(l)
    oz = savgol_filter(list(map(float, oz)), 225, 3)

    # 利用FFT bin获得BNR
    BNR = getBNR(oz, fs)

    return oz, BNR


def autoCo(data):
    # , ax1, ax2, ax3, ax4, ax5, ax6
    """
    本函数计算ACF和第一峰值对应的CSI序列的周期 data.shape = (F,T)
    输入CSI商的投影矩阵F*T,输出F*1的序列周期 peak1.shape = (30,)
    """
    F = data.shape[0]
    # print('子载波数:', F)
    peak1 = np.zeros(F)
    for i in range(F):
        ACF_temp = sm.tsa.acf(data[i, :], nlags=1000)
        peaks, _ = find_peaks(ACF_temp)
        if len(peaks):
            peak1[i] = int(peaks[0])
    return peak1


def MRC_period(BNR, period):
    nBNR = BNR / np.sum(BNR)
    return np.sum(np.multiply(nBNR, period))


def mergeoc(Bnr, aOz):
    '''
    Bnr.shape A * F'
    aOz.shape A * F' * T
    '''
    if Bnr.shape[0] == aOz.shape[0]:
        A = Bnr.shape[0]
    else:
        print('mergeoc error: dimension A is not consistent！')
    if Bnr.shape[1] == aOz.shape[1]:
        F = Bnr.shape[1]
    else:
        print('mergeoc error: dimension F is not consistent！')

    aoz = np.zeros([A, aOz.shape[2]])
    for ai in range(A):
        nBNR = Bnr[ai, :] / np.sum(Bnr[ai, :], axis=0)
        aoz[ai, :] = np.dot(nBNR, aOz[ai, :, :])
    return aoz


def detect_breath(raw_CSI, fw=100):
    breath_radio = csi_radio(raw_CSI)
    A = breath_radio.shape[0]
    F = breath_radio.shape[1]
    T = breath_radio.shape[2]  # 1200
    tw = T - fw * 2

    Bnr = np.zeros((A, F))
    aOz = np.zeros((A, F, tw))
    # print('aOz.shape', aOz.shape)
    for a in range(A):  # 遍历所有天线上的所有子载波上的数据
        for f in range(F):
            # try:
            SCr = breath_radio[a, f, :]
            # print('SCr.shape', SCr.shape)
            SC_real, SC_imag = savgol(SCr, 225)
            SC_real = SC_real[fw:-fw]  # 真实每次用于估算呼吸率的数据是tw个
            SC_imag = SC_imag[fw:-fw]
            # print(SCr)
            oz, BNR = PCAozandBNR(SC_real, SC_imag, fs=100)
            # print('oz:', oz, BNR)
            # print('oz.shape:', oz.shape)
            Bnr[a, f] = BNR
            aOz[a, f, :] = oz
            # print('第{}ret第{}子载波的BNR:{}'.format(a, f, BNR))
        # except ValueError:
        #     print(ValueError)

    Breath_rate = np.zeros(A)
    for ai in range(A):  # aOz 是 A * F * tw
        # 获得各个子载波上的rpm
        data = aOz[ai, :, :]  # F * tw
        peak1 = autoCo(data)  # F
        rpm = 60 / (peak1 / 100)  # F
        # print('rpm', rpm)
        # print('Bnr over {}:'.format(ai), Bnr[ai, :])
        # 剔除了rpm异常的子载波
        BNR, idx1 = binRemove(Bnr[ai, :], rpm, 0)
        # print('idx1:', idx1)
        # print('Bnr over {}:'.format(ai), BNR)
        # 根据BNR最大值剔除BNR不合格的子载波
        mBNR = np.max(Bnr)
        idx2 = BNR > 0.7 * mBNR
        idx = idx1 & idx2
        # print('index:',idx)
        BNR = BNR[idx]
        rpm = rpm[idx]
        Breath_rate[ai] = MRC_period(BNR, rpm)
    br = np.mean(Breath_rate)
    aoz = mergeoc(Bnr, aOz)
    return aoz, br


def extract(raw_CSI, his, an=0):
    '''
    :param raw_CSI: 输入raw_CSI，进行呼吸波形和呼吸率提取
    :return: data (packet number,)
    '''
    aoz, rpm = detect_breath(raw_CSI)
    if np.max(aoz) - np.min(aoz) < 0.1:
        print('未检测到人体存在')
        rpm = 0
        oc = np.random.randn(500) / 10000
        oc = (oc - (oc[0] - his))
        wave = [list(oc), rpm]
    if rpm < 11 or rpm > 37:  # 实验验证，存在抖腿，挠痒等持续时间较长的小动作时，会破坏周期性导致rpm异常
        print('big_motion or breath stop{}'.format(rpm))
        oc = np.random.randn(500) / 10000
        oc = (oc - (oc[0] - his))
        wave = [list(oc), rpm]
    else:
        x = 100
        oc = aoz[an, -x - 500:-x] - np.mean(aoz[an, -x - 500:-x])  # 拼接
        oc = (oc - (oc[0] - his))
        wave = [list(oc), rpm]
        print('breath_detect at {}rpm'.format(rpm))
    # print('len(wave)', len(wave[0]))  ：len(wave) 500
    print('rpm', wave[1])
    return wave
