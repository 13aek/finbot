from glob import glob
import os

print(glob(os.getcwd()+"/**/qdrant_localdb", recursive=True))