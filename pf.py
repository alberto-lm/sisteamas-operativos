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
relocation_queue = []
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

def add_process_to_stats(n_pages, process_id, size):
    '''Adds a new process to the stats dictionary.'''
    # A process that is currently in memory cannot be loaded more than once.
    if process_id in stats and stats[process_id]["active_bit"] == 1:
        print(f'Process {process_id} is already in memory, free the process to load it again.')
        return 1
    new_process = {
        "arrival_time": timer,
        "end_time": -1,
        "page_faults": 0,
        "swap_outs": 0,
        "swap_ins": 0,
        "pages": n_pages,
        "size": size,
        "active_bit": 1
    }
    stats[process_id] = new_process
    return 0
     
def insert_page_in_ram(page_key, ram_frame):
    '''Adds a new page to the page table.'''
    global timer
    relocation_queue.append(page_key)
    #When adding a new page it should always be loaded in main memory, disk_page = -1.
    page_table[page_key] = {
        "presence_bit": 1,
        "dirty_bit": 0,
        "ram_frame": ram_frame,
        "disk_frame": -1
    }
    timer += 1

def delete_key_in_queue(page_key):
    '''Deletes an element from the relocation queue.'''
    if page_key in relocation_queue:
        relocation_queue.pop(relocation_queue.index(page_key))

def move_page_to_front(page_key):
    '''Moves a page stored in the relocation queue to the front.'''
    delete_key_in_queue(page_key)
    relocation_queue.append(page_key)

def swap_page_out_of_ram(page_key, disk_frame):
    '''Moves a page from main memory to disk storage.'''
    global timer
    delete_key_in_queue(page_key)
    process_swapped_out, page_swapped_out = page_key.split('_')
    page_table[page_key]["presence_bit"] = 0
    page_table[page_key]["ram_frame"] = -1
    page_table[page_key]["disk_frame"] = disk_frame
    stats[process_swapped_out]["swap_outs"] += 1
    timer += 1
    print(f'Página {page_swapped_out} del proceso {process_swapped_out} swappeada al marco {disk_frame} del área de swapping')

def swap_page_in_ram(page_key, ram_frame, disk_frame):
    '''Moves a page from disk to ram storage.'''
    global timer
    relocation_queue.append(page_key)
    process_swapped_in, page_swapped_in = page_key.split('_')
    page_table[page_key]["presence_bit"] = 1
    page_table[page_key]["ram_frame"] = ram_frame
    page_table[page_key]["disk_frame"] = -1
    stats[process_swapped_in]["swap_ins"] += 1
    timer += 1
    print(f'Se localizó la página {page_swapped_in} del proceso {process_swapped_in} que estaba en la posición {disk_frame} de swapping y se cargó al marco {ram_frame}.')

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
    # Save pages in ram.
    continuous_frames_ram = []
    diff = 0
    pivot = ram[-1] if len(ram) > 0 else -1
    while len(ram) > 0 and process_pages > 0:
        # Page key to be inserted in ram.
        page_key = f'{process_id}_{process_pages-1}'
        # Ram frame where the new page will be inserted.
        ram_frame = ram.pop()
        insert_page_in_ram(page_key, ram_frame)
        # If the ram pages are not continuous.
        if pivot - ram_frame > diff:
            # Save the continuous pages, which are between pivot and pivot - diff + 1
            continuous_frames_ram.append((pivot - diff + 1, pivot))
            # Set the new pivot and reset the difference
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
        # Page key to be inserted in ram.
        page_key = f'{process_id}_{process_pages-1}'
        # Get the page key to be swapped out of ram.
        page_key_swapped_out = relocation_queue.pop(0)
        # Get the frame in ram that contains the page that is going to be swapped out.
        ram_frame_swapped_out = page_table[page_key_swapped_out]["ram_frame"]
        # Get the fram in disk that is going to receive the page swapped out.
        disk_frame = disk.pop()
        # Swap the page out of ram.
        swap_page_out_of_ram(page_key_swapped_out, disk_frame)
        # Insert the new page in the free frame in ram.
        insert_page_in_ram(page_key, ram_frame=ram_frame_swapped_out)
        process_pages -= 1

def access_page(cmd):
    """
        Displays a physical direction given a virtual direction.
        If the page that corresponds to the virtual direction is not sotored in ram,
        it fetches the direction in disk and swaps content between ram and disk.

        Parameters:
            cmd: (Tuple) Command to access a direction, contains virtual direction, process id and dirty bit.
    """
    if len(cmd) == ParamsNumber.ACCESS.value:
        try:
            virtual_direction = int(cmd[1])
            dirty_bit = int(cmd[3])
            process_id = cmd[2]
            if process_id not in stats or stats[process_id]["active_bit"] == 0 or virtual_direction > stats[process_id]["size"]:
                print(f'Error: Segementation Fault. Process {process_id} does not exist')
            else:
                global timer, algorithm
                print(f'{cmd[0]} {virtual_direction} {process_id} {dirty_bit}')
                print(f'Obtener la dirección real correspondiente a la dirección virtual {virtual_direction} del proceso {process_id}')
                logic_page = int(virtual_direction / PAGE_SIZE)
                access_page_key = f'{process_id}_{logic_page}'
                page_table[access_page_key]["dirty_bit"] = dirty_bit
                timer += 0.1
                if dirty_bit == 1:
                    print(f'Página {logic_page} del proceso {process_id} modificada')
                    timer += 0.1
                if page_table[access_page_key]["presence_bit"] == 0:
                    # Mark the page fault.
                    stats[process_id]["page_faults"] += 1
                    # Get disk frame where the direction to be accessed resides.
                    disk_frame = page_table[access_page_key]["disk_frame"]
                    # Get page to be swapped out of ram.
                    page_key_swapped_out = relocation_queue.pop(0)
                    # Get the frame in ram that is going to receive the page stored in disk.
                    ram_frame_swap_in = page_table[page_key_swapped_out]["ram_frame"]
                    # Execute swap out and update stats.
                    swap_page_out_of_ram(page_key_swapped_out, disk_frame)
                    # Store in ram the frame previously stored in disk (swap in) and update stats.
                    swap_page_in_ram(access_page_key, ram_frame_swap_in, disk_frame)
                else:
                    if algorithm == "lru":
                        move_page_to_front(access_page_key)
                real_direction = page_table[access_page_key]["ram_frame"] * PAGE_SIZE + virtual_direction % PAGE_SIZE
                print(f'Dirección virtual = {virtual_direction}. Dirección real = {real_direction}')
        except ValueError:
            print("Second and fourth parameters should be integers.")
    else:
        print("Incorrect number of parametes.")
    
def save_process(cmd):
    """
        Executes all the actions needed to insert a new process.
        It adds pages in main memory, swaps content out of ram if necessary,
        and updates the stats and page tables as well as fifo and lru lists.

        Parameters:
            cmd: (Tuple) representing P command. Contains the number of bytes to store and process id.
    """
    if len(cmd) == ParamsNumber.INSERT.value:
        try:
            size_bytes = int(cmd[1])
            process_id = cmd[2]
            n_pages = math.ceil(size_bytes / PAGE_SIZE)
            if size_bytes > RAM_SIZE or n_pages - len(ram) > len(disk) or n_pages == 0:
                print("It is not possible to allocate the process.")
            else:
                error = add_process_to_stats(n_pages, process_id, size_bytes)
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
            cmd: (Tuple) representing P command. Contains the process id.
    """
    if len(cmd) == ParamsNumber.FREE.value:
        process_id = cmd[1]
        if process_id not in stats or stats[process_id]["active_bit"] == 0:
            print(f'Could not find process {process_id}')
        else:
            global timer
            # Print command.
            print(f'{cmd[0]} {process_id}')
            # Stop the process.
            stats[process_id]["active_bit"] = 0
            n_pages = stats[process_id]["pages"]
            # Increment timer and set end time for the process.
            timer += n_pages * 0.1
            stats[process_id]["end_time"] = timer
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
                delete_key_in_queue(page_key)
                # Free space in page table.
                del page_table[page_key]
            ram.sort()
            disk.sort()
            if len(ram_free_frames) > 0:
                freed_frames = merge_continuous_frames(ram_free_frames)
                print(f'Se liberan los marcos de memoria real: {freed_frames}')
            if len(disk_free_frames) > 0:
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
            print("Empty line.")
        elif cmd[0] == Operation.ACCESS.value:
            access_page(cmd)
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