# LoL LCU Mobile Bridge

Bu repo, League of Legends LCU istemcisini okuyup mobil web arayüzünden şampiyon/rün/büyü yönetimi yapman için hazırlanmış projeyi içerir.

## Yapı
- `live_server.py`: FastAPI ana sunucu
- `lcu_backend/`: LCU bağlantı ve iş mantığı
- `mobile-panel/`: React + TypeScript mobil arayüz
- `start_server.py`: Backend başlatma scripti

## Kurulum
```bash
pip install -r requirements.txt
```

Frontend geliştirme:
```bash
cd mobile-panel
npm install
npm run dev
```

Backend:
```bash
python start_server.py
```

## Windows Tek Sefer Kurulum ve Servis Gibi Çalıştırma

### 1) Paket üret
```powershell
cd windows
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

### 2) Tek seferlik kurulum (otomatik açılış + firewall)
```powershell
powershell -ExecutionPolicy Bypass -File .\install_once.ps1 -RunNow
```

Kurulumdan sonra backend her Windows oturum açılışında arka planda çalışır.

### 3) Link / QR dosyaları
Her açılışta güncel LAN IP ile link üretilir ve aşağıya yazılır:
- `%LOCALAPPDATA%\\LolMakroBridge\\latest-link.txt`
- `%LOCALAPPDATA%\\LolMakroBridge\\latest-qr.png`

Notlar:
- Varsayılan port: `8765`
- Farklı port için: `install_once.ps1 -Port 9000`
- Dış ağ/tunnel URL'i sabitlemek için `LOL_BRIDGE_PUBLIC_URL` kullanabilirsin.
