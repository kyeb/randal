use rppal::gpio::{Gpio, Mode};

fn main() {
    // Access the GPIO
    let gpio = Gpio::new().unwrap();

    // Set pin BCM21 as an output
    let mut pin = gpio.get(21).unwrap().into_output();

    // Toggle the pin on and off every second
    loop {
        pin.set_high();
        std::thread::sleep(std::time::Duration::from_millis(1000));
        pin.set_low();
        std::thread::sleep(std::time::Duration::from_millis(1000));
    }
}
