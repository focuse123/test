import statsmodels.api as sm
from read_BF_file import *  # 数据读取和存储


def Gcsi(raw_CSI):
    '''
    计算功率响应
    '''
    # print('GCSI')
    # print(raw_CSI.shape)
    one = raw_CSI[0, :, :]
    two = raw_CSI[1, :, :]
    three = raw_CSI[2, :, :]
    Gone = one * np.conj(one)
    Gtwo = two * np.conj(two)
    Gthree = three * np.conj(three)
    G_Csi = np.array([Gone, Gtwo, Gthree]).real
    # print('Gcsi shape:', G_Csi.shape)
    return G_Csi


def subACF(one_subcarrier_data, Fs=100):
    '''计算单个子载波的运动统计量'''
    ACF_temp = sm.tsa.acf(one_subcarrier_data, unbiased=None, nlags=Fs, qstat=False, fft=False, alpha=None,
                          missing='none')
    # pylab.plot(ACF_temp)
    return ACF_temp[1]


def AllACF(Gcsi):
    A, F = Gcsi.shape[0], Gcsi.shape[1]
    motion = np.zeros((Gcsi.shape[0], Gcsi.shape[1]))
    for i in range(A):
        for j in range(F):
            motion[i, j] = subACF(Gcsi[i, j, :], Fs=100)
    return np.mean(motion)


def motion_detect(raw_CSI, thr):
    G_csi = Gcsi(raw_CSI)
    motion = AllACF(G_csi)
    if motion > thr:
        flag = False
    else:
        print('motion:', motion)
        flag = True
    return flag
