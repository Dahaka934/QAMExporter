from tkinter import filedialog

from nbt import *

file_path = filedialog.askopenfilename()

with open(file_path, 'rb') as io:
  nbt = NBTFile(io)
  text = nbt.pretty()

with open(file_path + ".txt", 'w') as io:
    io.write(text)