import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # Force GPU 0

import torch
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

from FYP25S109  import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)  # Run flask application, start webserver, say debug = true
    