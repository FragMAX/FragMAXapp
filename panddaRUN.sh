#!/bin/bash
#!/bin/bash
#SBATCH -t 99:55:00
#SBATCH -J PanDDA
#SBATCH --exclusive
#SBATCH -N1
#SBATCH --cpus-per-task=48
#SBATCH --mem=220000
#SBATCH -o /data/visitors/biomax/20180479/20190330/fragmax/logs/panddarun_%j.out
#SBATCH -e /data/visitors/biomax/20180479/20190330/fragmax/logs/panddarun_%j.err
module purge
module load CCP4 PyMOL

python /data/visitors/biomax/20180479/20190330/fragmax/scripts/checkPanDDA.py /data/visitors/biomax/20180479/20190330 xdsapp_dimple EPF2XEntry F2XEntry
