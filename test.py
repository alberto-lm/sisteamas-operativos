def merge_continuous_frames(arr):
    '''Returns an string with continuous frames grouped together.'''
    if len(arr) == 1:
        return arr[0]
    arr.sort()
    continuous_frames_str = ""
    diff = 0
    pivot = arr[0]
    for frame in arr:
        if frame - pivot > diff:
            if diff == 1:
                continuous_frames_str += f'{pivot}, '
            else:
                continuous_frames_str += f'{pivot}-{pivot + diff - 1}, '
            pivot = frame
            diff = 0
        diff += 1
    if diff == 1:
        continuous_frames_str += f'{pivot}'
    else:
        continuous_frames_str += f'{pivot}-{pivot + diff - 1}'
    return continuous_frames_str

arr = [1, 2, 3, 5, 6, 7, 10, 11, 34, 35, 36, 80]
print(merge_continuous_frames(arr))