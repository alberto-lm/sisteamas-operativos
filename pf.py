import argparse
import math
from enum import Enum

timer = 0
algorithm = "fifo"
PAGE_SIZE = 16
RAM_SIZE = 2048
DISK_SIZE = 4096

ram = []
disk = []
fifo = []
lru = []
page_table = {}
stats = {}


class Operation(Enum):
    '''Readable name for each operation.'''
    INSERT = 'P'
    ACCESS = 'A'
    FREE = 'L'
    COMMENT = 'C'
    END = 'F'
    EXIT = 'E'

class ParamsNumber(Enum):
    '''Expected number of parameters for each command.'''
    INSERT = 3
    ACCESS = 4
    FREE = 2
    END = 1
    EXIT = 1

def init_storage():
    '''Initializes the ram and disk storage spaces (free frames).'''
    for i in range(int(RAM_SIZE / PAGE_SIZE)):
        ram.append(i)
        disk.append(i)
    for i in range(int(RAM_SIZE / PAGE_SIZE), int(DISK_SIZE / PAGE_SIZE)):
        disk.append(i)

def add_process_to_stats(n_pages, process_id):
    '''Adds a new process to the stats dictionary.'''
    # A process that is currently in memory cannot be loaded more than once.
    if process_id in stats and stats[process_id]["active_bit"] == 1:
        print(f'Process {process_id} is already in memory, free the process to load it again.')
        return 1
    new_process = {
        "arrival_time": timer,
        "page_faults": 0,
        "swap_outs": 0,
        "swap_ins": 0,
        "pages": n_pages,
        "active_bit": 1
    }
    stats[process_id] = new_process
    return 0
     
def insert_page_in_ram(page_key, ram_frame):
    '''Adds a new page to the page table.'''
    global timer
    #When adding a new page it should always be loaded in main memory, disk_page = -1.
    page_table[page_key] = {
        "presence_bit": 1,
        "modification_bit": 0,
        "ram_frame": ram_frame,
        "disk_frame": -1
    }
    timer += 1

def swap_page_out_of_ram(page_key, disk_frame):
    '''Moves a page from main memory to disk storage.'''
    global timer
    page_table[page_key]["presence_bit"] = 0
    page_table[page_key]["ram_frame"] = -1
    page_table[page_key]["disk_frame"] = disk_frame
    timer += 1

def format_frame_ranges(frames):
    '''Groups continuous frames.'''
    ranges = ""
    for frame in frames:
        if frame[0] == frame[1]:
            ranges += f'{frame[0]}, '
        else:
            ranges += f'{frame[0]}-{frame[1]}, '
    return ranges[:-2]

def insert_pages(process_pages, process_id):
    """
        Allocates a certain number of pages in main memory.
        If necessary, it inserts the remaining pages in disk storage.

        Parameters:
            process_pages: (int) Number of pages to be allocated for the process.
            process_id: (str) Identifier for the new process.
    """
    global algorithm
    queue = fifo if algorithm == "fifo" else lru
    # Save pages in ram.
    continuous_frames_ram = []
    diff = 0
    pivot = ram[-1] if len(ram) > 0 else -1
    while len(ram) > 0 and process_pages > 0:
        page_key = f'{process_id}_{process_pages-1}'
        queue.append(page_key)
        ram_frame = ram.pop()
        insert_page_in_ram(page_key, ram_frame)
        if pivot - ram_frame > diff:
            continuous_frames_ram.append((pivot - diff + 1, pivot))
            pivot = ram_frame
            diff = -1
        process_pages -= 1
        diff += 1
    if pivot >= 0:
        continuous_frames_ram.append((pivot - diff + 1, pivot))
        frames_assigned = format_frame_ranges(continuous_frames_ram)
        print(f'Se asignaron los marcos de página {frames_assigned} al proceso {process_id}')
    # Save pages in disk.
    while process_pages > 0:
        page_key = f'{process_id}_{process_pages-1}'
        page_key_swapped_out = fifo.pop(0) if algorithm == "fifo" else lru.pop(0)
        queue.append(page_key)
        process_swapped, page_swapped = page_key_swapped_out.split('_')
        ram_frame_swapped_out = page_table[page_key_swapped_out]["ram_frame"]
        disk_frame = disk.pop()
        swap_page_out_of_ram(page_key_swapped_out, disk_frame)
        stats[process_swapped]["swap_outs"] += 1
        insert_page_in_ram(page_key, ram_frame=ram_frame_swapped_out)
        process_pages -= 1
        print(f'Página {page_swapped} del proceso {process_swapped} swappeada al marco {disk_frame} del área de swapping')
    
def save_process(cmd):
    """
        Executes all the actions needed to insert a new process.
        It adds pages in main memory, swaps content out of ram if necessary,
        and updates the stats and page tables as well as fifo and lru lists.

        Parameters:
            cmd: (Tuple) representing P command.

    """
    if len(cmd) == ParamsNumber.INSERT.value:
        try:
            size_bytes = int(cmd[1])
            process_id = cmd[2]
            n_pages = math.ceil(size_bytes / PAGE_SIZE)
            if size_bytes > RAM_SIZE or n_pages - len(ram) > len(disk) or n_pages == 0:
                print("It is not possible to allocate the process.")
            else:
                error = add_process_to_stats(n_pages, process_id)
                if error == 0:
                    print(f'{cmd[0]} {size_bytes} {process_id}')
                    print(f'Asignar {size_bytes} bytes al proceso {process_id}')
                    insert_pages(n_pages, process_id)
        except ValueError:
            print("Second parameter should be an integer.")
    else:
        print("Incorrect number of parametes.")

def free_space(cmd):
    """
        Frees space in ram and disk that is related with a certain process.
        Structures fifo and lru are also freed. 

        Parameters:
            cmd: (Tuple) representing P command.

    """
    if len(cmd) == ParamsNumber.FREE.value:
        process_id = cmd[1]
        if process_id not in stats or stats[process_id]["active_bit"] == 0:
            print(f'Could not find process {process_id}')
        else:
            global algorithm
            queue = fifo if algorithm == "fifo" else lru
            # Stop the process.
            stats[process_id]["active_bit"] = 0
            n_pages = stats[process_id]["pages"]
            ram_free_frames = []
            disk_free_frames = []
            for i in range(n_pages):
                page_key = f'{process_id}_{i}'
                # Free space in ram and disk.
                if page_table[page_key]["presence_bit"] == 0:
                    frame = page_table[page_key]["disk_frame"]
                    disk.append(frame)
                    disk_free_frames.append(frame)
                else:
                    frame = page_table[page_key]["ram_frame"]
                    ram.append(frame)
                    ram_free_frames.append(frame)
                # Free space in fifo or lru.
                if page_key in queue:
                    queue.pop(queue.index(page_key))
                # Free space in page table.
                del page_table[page_key]
            ram.sort()
            disk.sort()
            if len(ram_free_frames) > 0:
                freed_frames = merge_continuous_frames(ram_free_frames)
                print(f'Se liberan los marcos de memoria real: {freed_frames}')
            elif len(disk_free_frames) > 0:
                freed_frames = merge_continuous_frames(disk_free_frames)
                print(f'Se liberan los marcos de área de swapping: {freed_frames}')
    else:
        print("Incorrect number of parametes.")

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
            diff = -1
        diff += 1
    continuous_frames_str += f'{pivot}-{pivot + diff - 1}'
    return continuous_frames_str

def process_program(program):
    """
        Processes the program making the corresponding memory allocations, readings and swappings.

        Parameters:
            program: (list) Commands to be executed, as well as its parameters.

    """
    for cmd in program:
        if len(cmd) == 0:
            print("Emty line.")
        elif cmd[0] == Operation.ACCESS.value:
            print("ACCESS")
        elif cmd[0] == Operation.INSERT.value:
            save_process(cmd)
        elif cmd[0] == Operation.FREE.value:
            free_space(cmd)
        elif cmd[0] == Operation.COMMENT.value:
            print("COMMENT")
        elif cmd[0] == Operation.END.value:
            print("END")
        elif cmd[0] == Operation.EXIT.value:
            print("EXIT")
        else:
            print("Command not found")

def read_program(file_name):
    """
        Reads the text file provided as input and builds the program to be followed.

        Parameters:
            file_name: (str) Name of the file that contains the instructions.

        Returns:
            array: (list) Program instructions.

    """
    program = []
    input_file = open(file_name, 'r')
    for line in input_file:
        program.append(line.split())
    input_file.close()
    return program

def main():
    global algorithm
    parser = argparse.ArgumentParser()
    parser.add_argument('--swap', help='Relocation method: FIFO or LRU.', required=True)
    parser.add_argument('--file', help='Name of the input file', required=True)
    args = parser.parse_args()
    algorithm = args.swap
    file_name = args.file
    init_storage()
    program = read_program(file_name)
    process_program(program)


if __name__ == "__main__":
    main()