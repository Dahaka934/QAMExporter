import time

__all__ = (
    'profile', 'profile_print', 'print_profiler'
)

prof = {}
prof_level = 110

class profile:
    '''Function decorator for code profiling.'''

    def __init__(self, name, level=0):
        self.name = name
        self.level = level

    def __call__(self, fun):
        def profile_fun(*args, **kwargs):
            start = time.process_time()
            try:
                return fun(*args, **kwargs)
            finally:
                duration = time.process_time() - start
                if self.name not in prof:
                    prof[self.name] = [self.name, duration, 1]
                else:
                    it = prof[self.name]
                    it[1] += duration
                    it[2] += 1

        if self.level <= prof_level:
            return profile_fun
        else:
            return fun

class profile_print:
    def __call__(self, fun):
        def profile_print_fun(*args, **kwargs):
            try:
                return fun(*args, **kwargs)
            finally:
                print_profiler()
        return profile_print_fun

def print_profiler():
    '''Prints profiling results to the console. Run from a Python controller.'''

    def timekey(stat):
        return stat[1] / float(stat[2])
    stats = sorted(prof.values(), key=timekey, reverse=True)

    print('=== Execution Statistics ===')
    print('Times are in milliseconds.')
    print('{:<55} {:>6} {:>7} {:>6}'.format('FUNCTION', 'CALLS', 'SUM(ms)', 'AV(ms)'))
    for stat in stats:
        print('{:<55} {:>6} {:>7.0f} {:>6.2f}'.format(
            stat[0], stat[2],
            stat[1] * 1000,
            (stat[1] / float(stat[2])) * 1000))
    print('============================')
    prof.clear()
