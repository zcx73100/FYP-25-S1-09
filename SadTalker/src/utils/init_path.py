import os
import glob

def init_path(checkpoint_dir, config_dir, size=512, old_version=False, preprocess='crop'):
    # Debug: list files in the checkpoints folder
    print("[DEBUG] checkpoint_dir =", checkpoint_dir)
    if os.path.isdir(checkpoint_dir):
        print("[DEBUG] Contents of checkpoints folder:", os.listdir(checkpoint_dir))
    else:
        print("[ERROR] checkpoint_dir does not exist:", checkpoint_dir)

    # 1. If user explicitly wants old version
    if old_version:
        print("[INFO] Using old_version=True, looking for .pth files (epoch_20.pth, etc.)")
        sadtalker_paths = {
            'wav2lip_checkpoint':      os.path.join(checkpoint_dir, 'wav2lip.pth'),
            'audio2pose_checkpoint':   os.path.join(checkpoint_dir, 'auido2pose_00140-model.pth'),
            'audio2exp_checkpoint':    os.path.join(checkpoint_dir, 'auido2exp_00300-model.pth'),
            'free_view_checkpoint':    os.path.join(checkpoint_dir, 'facevid2vid_00189-model.pth.tar'),
            'path_of_net_recon_model': os.path.join(checkpoint_dir, 'epoch_20.pth')
        }
        use_safetensor = False

    else:
        # 2. Attempt to find a safetensor file
        safetensor_files = glob.glob(os.path.join(checkpoint_dir, '*.safetensors'))
        if safetensor_files:
            file_underscore = f'SadTalker_V0.0.2_{size}.safetensors'
            file_dash       = f'SadTalker_V0.0.2-{size}.safetensors'
            path_underscore = os.path.join(checkpoint_dir, file_underscore)
            path_dash       = os.path.join(checkpoint_dir, file_dash)

            if os.path.exists(path_underscore):
                chosen_file = path_underscore
            elif os.path.exists(path_dash):
                chosen_file = path_dash
            else:
                chosen_file = safetensor_files[0]
                print(f"[WARNING] Could not find {file_underscore} or {file_dash}. Using: {chosen_file}")

            print("[INFO] Using safetensor as default:", chosen_file)
            sadtalker_paths = {
                "checkpoint": chosen_file
            }
            use_safetensor = True
        else:
            # 3. Fallback to old version .pth if no .safetensors found
            print("[WARNING] No .safetensors found. Falling back to old version .pth.")
            sadtalker_paths = {
                'wav2lip_checkpoint':      os.path.join(checkpoint_dir, 'wav2lip.pth'),
                'audio2pose_checkpoint':   os.path.join(checkpoint_dir, 'auido2pose_00140-model.pth'),
                'audio2exp_checkpoint':    os.path.join(checkpoint_dir, 'auido2exp_00300-model.pth'),
                'free_view_checkpoint':    os.path.join(checkpoint_dir, 'facevid2vid_00189-model.pth.tar'),
                'path_of_net_recon_model': os.path.join(checkpoint_dir, 'epoch_20.pth')
            }
            use_safetensor = False

    # BFM fitting + config paths
    sadtalker_paths['dir_of_BFM_fitting'] = config_dir
    sadtalker_paths['audio2pose_yaml_path'] = os.path.join(config_dir, 'auido2pose.yaml')
    sadtalker_paths['audio2exp_yaml_path'] = os.path.join(config_dir, 'auido2exp.yaml')
    sadtalker_paths['use_safetensor'] = use_safetensor

    # 4. Mapping net + facerender config
    if 'full' in preprocess:
        sadtalker_paths['mappingnet_checkpoint'] = os.path.join(checkpoint_dir, 'mapping_00109-model.pth.tar')
        sadtalker_paths['facerender_yaml'] = os.path.join(config_dir, 'facerender_still.yaml')
    else:
        sadtalker_paths['mappingnet_checkpoint'] = os.path.join(checkpoint_dir, 'mapping_00229-model.pth.tar')
        sadtalker_paths['facerender_yaml'] = os.path.join(config_dir, 'facerender.yaml')

    return sadtalker_paths
