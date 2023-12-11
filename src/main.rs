use axum::{
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post},
    Extension, Router,
};
use rppal::gpio::Gpio;
use sled::Db;

#[tokio::main]
async fn main() {
    let db = init_db();
    let db_clone = db.clone();
    tokio::task::spawn_blocking(|| sensor_loop(db_clone));

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

fn sensor_loop(db: Db) {
    let gpio = Gpio::new().unwrap();

    let mut pin = gpio.get(21).unwrap().into_output();

    loop {
        if let Ok(Some(light_state)) = db.get("light_state") {
            if light_state == "on" {
                pin.set_high();
            } else {
                pin.set_low();
            }
        } else {
            pin.set_low();
        }
        std::thread::sleep(std::time::Duration::from_millis(100));
    }
}

async fn root() -> &'static str {
    "randal is alive!"
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
