use axum::{
    http::StatusCode,
    response::{Html, IntoResponse},
    routing::{get, post},
    Extension, Router,
};
use mpu9250::Mpu9250;
use rppal::{
    gpio::Gpio,
    spi::{Bus, Mode, SlaveSelect, Spi},
};
use sled::Db;

#[tokio::main]
async fn main() {
    let db = init_db();
    let db_clone = db.clone();
    tokio::task::spawn_blocking(|| hardware_loop(db_clone));

    let app = Router::new()
        .route("/", get(root))
        .route("/flip_light", post(flip_light))
        .fallback(handle_404)
        .layer(Extension(db));

    let listener = tokio::net::TcpListener::bind("0.0.0.0:5779").await.unwrap();

    axum::serve(listener, app).await.unwrap();
}

fn init_db() -> sled::Db {
    let db = sled::open("/tmp/main_db");
    match db {
        Ok(db) => {
            println!("Database opened");
            return db;
        }
        Err(db) => {
            panic!("Failed to open database: {:?}", db);
        }
    }
}

fn hardware_loop(db: Db) {
    let gpio = Gpio::new().unwrap();

    // if this works on the first try i will literally drop my jaw to the floor
    let mut led_pin = gpio.get(21).unwrap().into_output();
    let ncs_pin = gpio.get(8).unwrap().into_output();
    let mut delay = rppal::hal::Delay::new();

    // Mode3: CPOL 1, CPHA 1 (based on mpu9250::MODE)
    let spi = Spi::new(Bus::Spi0, SlaveSelect::Ss0, 1_000_000, Mode::Mode3);
    if spi.is_err() {
        println!("Failed to initialize SPI: {:?}", spi.err().unwrap());
        return;
    }
    let spi = spi.unwrap();

    let mpu = Mpu9250::imu_default(spi, ncs_pin, &mut delay);

    if mpu.is_err() {
        println!("Failed to initialize MPU9250: {:?}", mpu.err().unwrap());
        return;
    }

    let mut mpu = mpu.unwrap();

    loop {
        // if let Ok(Some(light_state)) = db.get("light_state") {
        //     if light_state == "on" {
        //         led_pin.set_high();
        //     } else {
        //         led_pin.set_low();
        //     }
        // } else {
        //     led_pin.set_low();
        // }

        let data = mpu.all::<[f32; 3]>().unwrap();
        if data.accel[2] < -5.0 {
            led_pin.set_high();
        } else {
            led_pin.set_low();
        }

        std::thread::sleep(std::time::Duration::from_millis(1000));
    }
}

async fn root() -> Html<&'static str> {
    Html(include_str!("index.html"))
}

async fn handle_404() -> impl IntoResponse {
    (StatusCode::NOT_FOUND, "nothing to see here")
}

async fn flip_light(db: Extension<Db>) -> &'static str {
    if let Ok(light_state) = db.get("light_state") {
        if let Some(light_state) = light_state {
            if light_state == "on" {
                db.insert("light_state", "off").unwrap();
                return "success: light flipped to off";
            } else {
                db.insert("light_state", "on").unwrap();
                return "success: light flipped to on";
            }
        } else {
            db.insert("light_state", "on").unwrap();
            return "success: light state initialized";
        }
    } else {
        return "failed to get light state";
    }
}
