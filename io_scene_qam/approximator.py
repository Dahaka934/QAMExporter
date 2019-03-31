from numpy import array
import math

try:
    import utils
except:
    from . import utils

__all__ = (
    'Approximator'
)

class Approximator:

    def __init__(self, size):
        self._size = size
        self._tmpVec = array([0.0 for i in range(0, size)])

    def approximate(self, points, err):
        indices = [0, len(points) - 1]
        idxs = []
        index, _ = self.calcMaxError(points, 0, len(points) - 1, err)
        if index != -1:
            idxs.append(index)

        while len(idxs) > 0:
            j = utils.binaryInsert(indices, idxs.pop())
            index, _ = self.calcMaxError(points, indices[j - 1], indices[j], err)
            if index != -1:
                idxs.append(index)

            index, _ = self.calcMaxError(points, indices[j], indices[j + 1], err)
            if index != -1:
                idxs.append(index)

        return indices

    def approximateIterable(self, points, indices, weights):
        if indices is None or len(indices) < 2:
            indices = [0, len(points) - 1]
            weights = [self.calcMaxError(points, indices[0], indices[1], -1)]
            return indices, weights

        maxIndex = self.findMaxError(weights)
        item = weights[maxIndex]

        if item[0] >= 0:
            j = utils.binaryInsert(indices, item[0])
            weights[j - 1] = self.calcMaxError(points, indices[j - 1], indices[j], -1)
            weights.insert(j, self.calcMaxError(points, indices[j], indices[j + 1], -1))

        return indices, weights

    def calcMaxError(self, points, init, end, err):
        index = -1
        if init > end:
            return index, 0
        maxValue = 0
        for i in range(init + 1, end):
            sqDis  = self.onLine(points[init], points[end], points[i])
            if sqDis > maxValue:
                maxValue = sqDis
                index = i
        if maxValue > err:
            return index, maxValue
        else:
            return -1, maxValue

    def findMaxError(self, weights):
        max = 0.0
        maxIndex = 0
        for idx, val in enumerate(weights):
            if val[1] > max:
                maxIndex = idx
                max = val[1]
        return maxIndex

    def onLine(self, p1, p2, pa):
        pd = self._tmpVec
        dsq = self.distanceSq(p1, p2, pd)
        if dsq == 0:
            return 0.0
        else:
            u = 0.0
            for i in range(0, len(p1)):
                u += (pa[i] - p1[i]) * pd[i]
            u /= dsq
            if u <= 0:
                return self.distanceSq(p1, pa, pd)
            elif u >= 1:
                return self.distanceSq(p2, pa, pd)
            else:
                for i in range(0, len(p1)):
                    pd[i] = p1[i] + u * pd[i]
                return self.distanceSq(pd, pa, pd)

    def distanceSq(self, p1, p2, pd):
        for i in range(0, len(p1)):
            pd[i] = p2[i] - p1[i]
        sum = 0.0
        for i in range(0, len(p1)):
            sum += pd[i]*pd[i]
        return sum
