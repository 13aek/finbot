import os
from glob import glob

print(glob(os.getcwd() + "/**/qdrant_localdb", recursive=True))
