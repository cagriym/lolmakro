# LoL Rune Page Manager — Mobile Panel

League Client ile senkron calisan, mobil uyumlu web arayuzu. Canli oyun verisini ve rune sayfasi yonetimini tek ekranda toplar.

## Ozellikler
- WebSocket ile gercek zamanli senkronizasyon
- Mobil uyumlu, dokunmatik odakli UI
- Canli mac istatistik paneli
- League of Legends temali tasarim

## Teknolojiler
- React 18 + TypeScript
- Vite
- Zustand
- React Router

## Kurulum
```bash
npm install
```

## Gelistirme
```bash
npm run dev
```

## Build
```bash
npm run build
npm run preview
```

## Ortam Degiskeni
`.env` dosyasina API adresini yazabilirsiniz:
```env
VITE_API_BASE=http://localhost:8000
```

## Notlar
- Backend tarafi calismali (LCU/WS servisleri).
- `src/services` altinda API ve WebSocket katmani bulunur.
