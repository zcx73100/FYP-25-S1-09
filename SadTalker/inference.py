from glob import glob
import shutil
import torch
from time import strftime
import os, sys, time
from argparse import ArgumentParser

from src.utils.preprocess import CropAndExtract
from src.test_audio2coeff import Audio2Coeff
from src.facerender.animate import AnimateFromCoeff
from src.generate_batch import get_data
from src.generate_facerender_batch import get_facerender_data
from src.utils.init_path import init_path

def main(args):
    # Get the absolute path to the directory containing inference.py.
    current_root_path = os.path.dirname(os.path.abspath(__file__))

    # Ensure checkpoint_dir is absolute.
    if not os.path.isabs(args.checkpoint_dir):
        args.checkpoint_dir = os.path.join(current_root_path, args.checkpoint_dir)

    # Ensure result_dir is absolute.
    if not os.path.isabs(args.result_dir):
        args.result_dir = os.path.join(current_root_path, args.result_dir)

    # Set config_dir to the src/config folder inside SadTalker.
    config_dir = os.path.join(current_root_path, 'src', 'config')

    # Debug prints for clarity
    print("[DEBUG] current_root_path:", current_root_path)
    print("[DEBUG] checkpoint_dir:", args.checkpoint_dir)
    print("[DEBUG] result_dir:", args.result_dir)
    print("[DEBUG] config_dir:", config_dir)

    # Initialize paths using absolute directories.
    sadtalker_paths = init_path(
        checkpoint_dir=args.checkpoint_dir,
        config_dir=config_dir,
        size=args.size,
        old_version=args.old_version,
        preprocess=args.preprocess
    )

    # Initialize models
    preprocess_model = CropAndExtract(sadtalker_paths, args.device)
    audio_to_coeff = Audio2Coeff(sadtalker_paths, args.device)
    animate_from_coeff = AnimateFromCoeff(sadtalker_paths, args.device)

    pic_path = args.source_image
    audio_path = args.driven_audio

    # Create a timestamped directory inside the result_dir.
    timestamp = strftime("%Y_%m_%d_%H.%M.%S")
    save_dir = os.path.join(args.result_dir, timestamp)
    os.makedirs(save_dir, exist_ok=True)

    pose_style = args.pose_style
    batch_size = args.batch_size
    input_yaw_list = args.input_yaw
    input_pitch_list = args.input_pitch
    input_roll_list = args.input_roll
    ref_eyeblink = args.ref_eyeblink
    ref_pose = args.ref_pose

    # 3DMM Extraction for source image.
    first_frame_dir = os.path.join(save_dir, 'first_frame_dir')
    os.makedirs(first_frame_dir, exist_ok=True)
    print('3DMM Extraction for source image')
    first_coeff_path, crop_pic_path, crop_info = preprocess_model.generate(
        pic_path,
        first_frame_dir,
        args.preprocess,
        source_image_flag=True,
        pic_size=args.size
    )
    if first_coeff_path is None:
        print("Can't get the coeffs of the input")
        sys.exit(1)

    if ref_eyeblink is not None:
        ref_eyeblink_videoname = os.path.splitext(os.path.split(ref_eyeblink)[-1])[0]
        ref_eyeblink_frame_dir = os.path.join(save_dir, ref_eyeblink_videoname)
        os.makedirs(ref_eyeblink_frame_dir, exist_ok=True)
        print('3DMM Extraction for the reference video providing eye blinking')
        ref_eyeblink_coeff_path, _, _ = preprocess_model.generate(
            ref_eyeblink, ref_eyeblink_frame_dir, args.preprocess, source_image_flag=False
        )
    else:
        ref_eyeblink_coeff_path = None

    if ref_pose is not None:
        if ref_pose == ref_eyeblink:
            ref_pose_coeff_path = ref_eyeblink_coeff_path
        else:
            ref_pose_videoname = os.path.splitext(os.path.split(ref_pose)[-1])[0]
            ref_pose_frame_dir = os.path.join(save_dir, ref_pose_videoname)
            os.makedirs(ref_pose_frame_dir, exist_ok=True)
            print('3DMM Extraction for the reference video providing pose')
            ref_pose_coeff_path, _, _ = preprocess_model.generate(
                ref_pose, ref_pose_frame_dir, args.preprocess, source_image_flag=False
            )
    else:
        ref_pose_coeff_path = None

    # Audio to coefficient conversion.
    batch = get_data(first_coeff_path, audio_path, args.device, ref_eyeblink_coeff_path, still=args.still)
    coeff_path = audio_to_coeff.generate(batch, save_dir, pose_style, ref_pose_coeff_path)

    # 3D face rendering visualization (optional).
    if args.face3dvis:
        from src.face3d.visualize import gen_composed_video
        gen_composed_video(
            args,
            args.device,
            first_coeff_path,
            coeff_path,
            audio_path,
            os.path.join(save_dir, '3dface.mp4')
        )

    # Prepare data for coefficient-to-video conversion.
    data = get_facerender_data(
        coeff_path,
        crop_pic_path,
        first_coeff_path,
        audio_path,
        batch_size,
        input_yaw_list,
        input_pitch_list,
        input_roll_list,
        expression_scale=args.expression_scale,
        still_mode=args.still,
        preprocess=args.preprocess,
        size=args.size
    )

    # This call should produce the final video in the "save_dir" folder as "temp_result.xxx"
    result = animate_from_coeff.generate(
        data,
        save_dir,
        pic_path,
        crop_info,
        enhancer=args.enhancer,
        background_enhancer=args.background_enhancer,
        preprocess=args.preprocess,
        img_size=args.size
    )

    # Keep the final video INSIDE the folder
    # Rename "result" file to "output.mp4" in the same folder
    final_video = os.path.join(save_dir, "output.mp4")
    shutil.move(result, final_video)

    print('The generated video is named:', final_video)
    print('FINAL_OUTPUT:', final_video)

    # If you do NOT want to keep intermediate files, you can re-enable the removal
    # but that would also remove the final mp4 if it's inside the folder.
    # So let's keep it commented out:
    #
    # if not args.verbose:
    #     shutil.rmtree(save_dir)

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("--driven_audio", default='./examples/driven_audio/bus_chinese.wav', help="path to driven audio")
    parser.add_argument("--source_image", default='./examples/source_image/full_body_1.png', help="path to source image")
    parser.add_argument("--ref_eyeblink", default=None, help="path to reference video providing eye blinking")
    parser.add_argument("--ref_pose", default=None, help="path to reference video providing pose")
    parser.add_argument("--checkpoint_dir", default='./checkpoints', help="relative path to checkpoints folder")
    parser.add_argument("--result_dir", default='./results', help="relative path to results folder")
    parser.add_argument("--pose_style", type=int, default=0, help="input pose style from [0, 46)")
    parser.add_argument("--batch_size", type=int, default=2, help="the batch size of facerender")
    parser.add_argument("--size", type=int, default=256, help="the image size of the facerender")
    parser.add_argument("--expression_scale", type=float, default=1., help="expression scale for facerender")
    parser.add_argument('--input_yaw', nargs='+', type=int, default=None, help="the input yaw degree of the user")
    parser.add_argument('--input_pitch', nargs='+', type=int, default=None, help="the input pitch degree of the user")
    parser.add_argument('--input_roll', nargs='+', type=int, default=None, help="the input roll degree of the user")
    parser.add_argument('--enhancer', type=str, default=None, help="Face enhancer, [gfpgan, RestoreFormer]")
    parser.add_argument('--background_enhancer', type=str, default=None, help="background enhancer, [realesrgan]")
    parser.add_argument("--cpu", dest="cpu", action="store_true")
    parser.add_argument("--face3dvis", action="store_true", help="generate 3D face and 3D landmarks")
    parser.add_argument("--still", action="store_true", help="enable still mode for full-body animation")
    parser.add_argument("--preprocess", default='crop', choices=['crop','extcrop','resize','full','extfull'], help="how to preprocess the images")
    parser.add_argument("--verbose", action="store_true", help="save intermediate output or not")
    parser.add_argument("--old_version", action="store_true", help="use old .pth checkpoint version instead of safetensors")

    # Additional (unused) parameters.
    parser.add_argument('--net_recon', type=str, default='resnet50', choices=['resnet18','resnet34','resnet50'], help='useless')
    parser.add_argument('--init_path', type=str, default=None, help='Useless')
    parser.add_argument('--use_last_fc', default=False, help='zero initialize the last fc')
    parser.add_argument('--bfm_folder', type=str, default='./checkpoints/BFM_Fitting/', help='BFM fitting folder')
    parser.add_argument('--bfm_model', type=str, default='BFM_model_front.mat', help='BFM model')

    # Renderer parameters.
    parser.add_argument('--focal', type=float, default=1015.)
    parser.add_argument('--center', type=float, default=112.)
    parser.add_argument('--camera_d', type=float, default=10.)
    parser.add_argument('--z_near', type=float, default=5.)
    parser.add_argument('--z_far', type=float, default=15.)

    args = parser.parse_args()

    # Decide CPU vs. GPU
    if torch.cuda.is_available() and not args.cpu:
        args.device = "cuda"
    else:
        args.device = "cpu"

    main(args)




