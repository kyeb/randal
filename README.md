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

### References

https://amritrathie.vercel.app/posts/2020/03/06/cross-compiling-rust-from-macos-to-raspberry-pi
