import multiprocessing as mp
import subprocess
import argparse
import numpy as np

DATA_MOUNT_POINT = '/home/ramtin/code/uni-thesis/CATER/generate/'
OUT_DIR = 'Out' 
NAME = "ARC-GEN"
CAM_MOTION = False
MAX_MOTIONS = 1
NUM_IMAGES = 20 #how many videos to generate
NUM_FRAMES = 100 #how many frames per video
FPS = 10



def parse_args():
    parser = argparse.ArgumentParser(description='Launch blender')
    parser.add_argument(
        '--gpus', '-g', default=None, type=str,
        help='GPUs to run on')
    parser.add_argument(
        '--num_jobs', '-n', default=1, type=int,
        help='Run n jobs per GPU')
    return parser.parse_args()


def get_gpu_count():
    count = int(subprocess.check_output(
        'ls /proc/driver/nvidia/gpus/ | wc -l', shell=True))
    return count


def run_blender(gpu_id):
    # sleep for a random time, to make sure it does not overlap!
    sleep_time = 1 + int(np.random.random() * 5)  # upto 6 seconds
    subprocess.call('sleep {}'.format(sleep_time), shell=True)

    blender_path='/opt/blender-2.79/blender'
    cam_motion='--random_camera' if CAM_MOTION else ''
    max_motions='--max_motions={}'.format(MAX_MOTIONS)

    cmd = f'CUDA_VISIBLE_DEVICES="{gpu_id}" \
            {blender_path} \
            data/base_scene.blend \
            --background --python render_videos.py -- \
            --num_images {NUM_IMAGES} \
            --num_frames {NUM_FRAMES} \
            --fps {FPS} \
            --suppress_blender_logs \
            --save_blendfiles 0 \
            {cam_motion} \
            {max_motions} \
            --filename_prefix {NAME} \
            --output_dir {DATA_MOUNT_POINT}{OUT_DIR} \
            --output_scene_file {DATA_MOUNT_POINT}{OUT_DIR}/scene.json \
            '

    print('Running {}'.format(cmd))
    subprocess.call(cmd, shell=True)


args = parse_args()
if args.gpus is None:
    ngpus = get_gpu_count()
    gpu_ids = list(range(ngpus))
else:
    gpu_ids = [int(el) for el in args.gpus.split(',')]
ngpus = len(gpu_ids)
print('Found {} GPUs. Using all of those.'.format(ngpus))
# Repeat jobs per GPU
gpu_ids *= args.num_jobs
pool = mp.Pool(len(gpu_ids))
pool.map(run_blender, gpu_ids)
