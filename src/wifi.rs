//! WiFi station + TCP telemetry/command server.
//!
//! All network work happens off the control loop: WiFi init and the TCP
//! server run in their own thread, telemetry crosses over via a bounded
//! channel that drops lines when full (same semantics as the UART TX ring),
//! and inbound command bytes are polled by the main loop exactly like UART
//! bytes. If WiFi never comes up, the robot runs identically to before.

use crate::wifi_secrets::{WIFI_PASS, WIFI_SSID};
use esp_idf_svc::eventloop::EspSystemEventLoop;
use esp_idf_svc::hal::modem::Modem;
use esp_idf_svc::nvs::EspDefaultNvsPartition;
use esp_idf_svc::sys;
use esp_idf_svc::wifi::{AuthMethod, BlockingWifi, ClientConfiguration, Configuration, EspWifi};
use log::{info, warn};
use std::io::{ErrorKind, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc::{sync_channel, Receiver, SyncSender};
use std::sync::OnceLock;
use std::time::Duration;

pub const TCP_PORT: u16 = 3333;

static TELEM_TX: OnceLock<SyncSender<String>> = OnceLock::new();
static CLIENT_CONNECTED: AtomicBool = AtomicBool::new(false);

/// Called from the control loop's telemetry path. Never blocks: no client or
/// full queue → the line is dropped.
pub fn telem_send(line: &str) {
    if !CLIENT_CONNECTED.load(Ordering::Relaxed) {
        return;
    }
    if let Some(tx) = TELEM_TX.get() {
        let _ = tx.try_send(line.to_string());
    }
}

/// Spawns the WiFi + TCP server thread. Returns the command-byte receiver the
/// main loop polls alongside UART. Never blocks the caller on network state.
pub fn start(modem: Modem) -> Receiver<u8> {
    let (telem_tx, telem_rx) = sync_channel::<String>(64);
    let (cmd_tx, cmd_rx) = sync_channel::<u8>(1024);
    let _ = TELEM_TX.set(telem_tx);

    std::thread::Builder::new()
        .name("wifi-srv".into())
        .stack_size(12 * 1024)
        .spawn(move || run(modem, telem_rx, cmd_tx))
        .unwrap();

    cmd_rx
}

fn run(modem: Modem, telem_rx: Receiver<String>, cmd_tx: SyncSender<u8>) {
    let sysloop = EspSystemEventLoop::take().unwrap();
    let nvs = EspDefaultNvsPartition::take().unwrap();

    let mut wifi = BlockingWifi::wrap(
        EspWifi::new(modem, sysloop.clone(), Some(nvs)).unwrap(),
        sysloop,
    )
    .unwrap();

    wifi.set_configuration(&Configuration::Client(ClientConfiguration {
        ssid: WIFI_SSID.try_into().unwrap(),
        password: WIFI_PASS.try_into().unwrap(),
        auth_method: AuthMethod::WPA2Personal,
        ..Default::default()
    }))
    .unwrap();
    wifi.start().unwrap();

    loop {
        match wifi.connect().and_then(|_| wifi.wait_netif_up()) {
            Ok(_) => break,
            Err(e) => {
                warn!("wifi connect failed ({e}), retrying in 3s");
                std::thread::sleep(Duration::from_secs(3));
            }
        }
    }

    // Power save adds 100-300ms latency spikes; this is a robot, not a sensor.
    unsafe {
        sys::esp_wifi_set_ps(sys::wifi_ps_type_t_WIFI_PS_NONE);
    }

    let ip = wifi.wifi().sta_netif().get_ip_info().unwrap().ip;
    info!("wifi up: {ip}:{TCP_PORT}");

    let listener = TcpListener::bind(("0.0.0.0", TCP_PORT)).unwrap();
    loop {
        match listener.accept() {
            Ok((stream, peer)) => {
                info!("tcp client connected: {peer}");
                // Drop telemetry queued while nobody was listening
                while telem_rx.try_recv().is_ok() {}
                CLIENT_CONNECTED.store(true, Ordering::Relaxed);
                serve_client(stream, &telem_rx, &cmd_tx);
                CLIENT_CONNECTED.store(false, Ordering::Relaxed);
                info!("tcp client disconnected");
                // Safety: a vanished operator shouldn't leave motion targets set
                for b in b"TVEL 0\nTYAW 0\n" {
                    let _ = cmd_tx.try_send(*b);
                }
            }
            Err(e) => {
                warn!("tcp accept failed: {e}");
                std::thread::sleep(Duration::from_secs(1));
            }
        }
    }
}

fn serve_client(mut stream: TcpStream, telem_rx: &Receiver<String>, cmd_tx: &SyncSender<u8>) {
    stream.set_nodelay(true).ok();
    stream.set_read_timeout(Some(Duration::from_millis(5))).ok();

    let mut rbuf = [0u8; 256];
    loop {
        // Telemetry out (recv_timeout paces the loop when idle)
        match telem_rx.recv_timeout(Duration::from_millis(20)) {
            Ok(line) => {
                if stream.write_all(line.as_bytes()).is_err() {
                    return;
                }
            }
            Err(std::sync::mpsc::RecvTimeoutError::Timeout) => {}
            Err(std::sync::mpsc::RecvTimeoutError::Disconnected) => return,
        }

        // Command bytes in
        match stream.read(&mut rbuf) {
            Ok(0) => return, // client closed
            Ok(n) => {
                for b in &rbuf[..n] {
                    let _ = cmd_tx.try_send(*b);
                }
            }
            Err(e) if e.kind() == ErrorKind::WouldBlock || e.kind() == ErrorKind::TimedOut => {}
            Err(_) => return,
        }
    }
}
