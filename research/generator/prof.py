import cProfile,pstats,sys
sys.path.insert(0,'research/generator'); sys.path.insert(0,'src')
import decoder
from elf import load
P=load(practice=True)
pz=P['practice_0015']
cProfile.run('decoder.decode(pz)','research/generator/prof.out')
pstats.Stats('research/generator/prof.out').sort_stats('tottime').print_stats(8)
