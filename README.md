## randal

a robot inspired by Boston Dynamics' Handle

## development

Since this runs on a Raspberry Pi, there are a few extra setup steps beyond a basic Rust install.

tl;dr:
```
# Install the Rust toolchain for ARM / Linux / musl
rustup target add armv7-unknown-linux-musleabihf

# Install some macOS-specific cross-compilation tooling
brew install arm-linux-gnueabihf-binutils 

# Configure cargo to use that tooling
echo "[target.armv7-unknown-linux-musleabihf]\nlinker = \"arm-linux-gnueabihf-ld\"" >> ~/.cargo/config  
```

## pi setup

1. [Raspberry Pi Imager](https://www.raspberrypi.com/software/) is a neat little utility to help configure a pi without having to remember all the little config file options. Set various things in the imager:
- Raspberry Pi OS Lite - skips desktop environment
- Set hostname to `pi`
- Set up username/password
- Set up WiFi SSID/password
- Enable SSH
- SSH public key

2. Install `ansible` on your local machine:
```
# macOS
brew install pipx
pipx ensurepath

# Ubuntu
sudo apt update
sudo apt install pipx
pipx ensurepath

# Arch
sudo pacman -Syu
sudo pacman -S python-pipx
pipx ensurepath

# and Ansible itself...
pipx install --include-deps ansible
```

3. Make sure your `ansible/hosts` file is pointing to your pi. You can verify this is configured properly with:
```bash
ansible pi -m ping -i ansible/inventory.ini
```

4. Run Ansible to set everything else up, theoretically!
```bash
ansible-playbook -i ansible/inventory.ini ansible/full-setup.yaml 
ansible-playbook -i ansible/inventory.ini ansible/randal-full.yaml
```


## references

https://amritrathie.vercel.app/posts/2020/03/06/cross-compiling-rust-from-macos-to-raspberry-pi

https://protosupplies.com/product/mpu-9250-3-axis-accel-gryo-mag-sensor-module/
