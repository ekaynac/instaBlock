# Instagram Engelleme Aracı (CLI)

Bu proje, instagrapi kütüphanesini kullanarak Instagram hesaplarını otomatik olarak engellemek amacıyla geliştirilmiş bir komut satırı aracıdır. Bu araç, hem kullanıcı tarafından sağlanan bir blacklist dosyası üzerinden hem de belirli bir Instagram hesabının takip ettiklerinden otomatik olarak oluşturulan başlangıç blacklist'ine göre çalışır.

## İçerik

- [Özellikler](#özellikler)
- [Kurulum](#kurulum)
- [Kullanım](#kullanım)
  - [Giriş Parametreleri](#giriş-parametreleri)
  - [Blacklist Dosyası](#blacklist-dosyası)
  - [Initial Blacklist Oluşturma](#initial-blacklist-oluşturma)
- [API İstek Yönetimi](#api-i̇stek-yönetimi)
- [Hesap Güvenliği ve Alınan Önlemler](#hesap-güvenliği-ve-alınan-önlemler)
- [Detaylı Süre Loglaması](#detaylı-süre-loglaması)
- [Ek Notlar](#ek-notlar)
- [İletişim](#iletişim)

## Özellikler

- **Blacklist Temelli Engelleme:**  
  Belirtilen bir TXT veya CSV dosyasındaki kullanıcı adlarına göre hesapları engeller.

- **Initial Blacklist Oluşturma:**  
  Belirli bir Instagram hesabının takip ettiklerinden otomatik olarak başlangıç blacklist'i oluşturur.

- **API İstek Persistansı:**  
  API isteklerinin zaman damgaları `api_request_log.json` dosyasında saklanır. Böylece script, restart edildiğinde son 1 saatte yapılan API çağrısı sayısını hesaplayabilir.

- **Dinamik Rate Limit Kontrolü:**  
  - Son 1 saatte 200 veya daha fazla API isteği yapıldıysa, script 1 saat bekler.  
  - 100 veya daha fazla API isteği yapıldıysa, engelleme işlemleri durdurulur ve her 1 dakikada JSON dosyası kontrol edilerek istek sayısı 50’ye düştüğünde işlemler devam eder.

- **Detaylı Loglama:**  
  Her adım detaylı olarak Türkçe loglanır. Her 10 başarılı engellemeden sonra kalan engellenmemiş hesap sayısı ve tahmini süre loglanır.

- **Güvenlik Önlemleri:**  
  - **Challenge Yönetimi:** ChallengeRequired durumunda, otomatik çözüm denenmez. Kullanıcıya, "Lütfen Instagram hesabınıza gidip challenge'ı manuel olarak çözün ve scripti yeniden başlatın." şeklinde talimat verilir.  
  - **Kullanıcı Adı Doğrulaması:** Blacklist dosyasındaki kullanıcı adları geçerli formatta (regex kontrolü) olup olmadığı kontrol edilir.  
  - **Log Filtresi:** Public endpoint’lerden gelen, "public_request" ve "JSONDecodeError" içeren hata mesajları filtrelenir, böylece gereksiz hata logları görüntülenmez.

## Kurulum

### Gereksinimler

- Python 3.6 veya üstü  
- [instagrapi](https://github.com/adw0rd/instagrapi) kütüphanesi

### Kurulum Adımları

1. **Repository'yi Klonlayın:**

   ```bash
   git clone https://github.com/<yourusername>/InstaBlocker.git
   cd InstaBlocker
   ```

2. **Gerekli Paketleri Yükleyin:**

   ```bash
   pip install instagrapi
   ```

3. **(Opsiyonel) Sanal Ortam Oluşturun:**

   ```bash
   python -m venv venv
   # Linux/Mac:
   source venv/bin/activate
   # Windows:
   venv\Scripts\activate
   ```

## Kullanım

### Giriş Parametreleri

- `--username`: Instagram kullanıcı adınız (giriş yapmak için).
- `--blacklist`: Engellenecek hesapların listesinin bulunduğu dosyanın yolu (TXT veya CSV).
- `--init-blacklist`: Hedef hesabın takip ettiklerinden başlangıç blacklist'i oluşturmak için (örneğin, bir URL veya kullanıcı adı).
- `--request-limit`: Saatlik API istek limiti (varsayılan: 100).

### Blacklist Dosyası

Blacklist dosyası iki formatta olabilir:

- **TXT Dosyası:** Her satırda bir kullanıcı adı.
- **CSV Dosyası:** En az `username` adlı sütun içermelidir.

Örnek CSV formatı:

```csv
username
user1
user2
user3
```

### Initial Blacklist Oluşturma

Belirli bir Instagram hesabının takip ettiklerinden otomatik olarak başlangıç blacklist'i oluşturmak için:

```bash
python boykot.py --username YOUR_USERNAME --init-blacklist https://www.instagram.com/target_account/
```

Bu komut, `target_account` hesabının takip ettiklerini `blacklist_target_account.txt` adlı dosyaya kaydeder.

### Engelleme Modu

Blacklist dosyası kullanarak engelleme işlemlerini başlatmak için:

```bash
python boykot.py --username YOUR_USERNAME --blacklist path/to/blacklist.txt --request-limit 100
```

Script, belirtilen dosyadaki hesapları engelleyecek, API isteklerini persist edecek ve dinamik olarak rate limit kontrollerini gerçekleştirecektir. Başarılı engelleme işlemleri sonrası 30 saniye, başarısız işlemler sonrası ise 60 saniye beklenir. Ayrıca, her 10 başarılı engellemeden sonra kalan engellenmemiş hesap sayısı ve tahmini süre loglanır.

## API İstek Yönetimi

- **Persistent API Log:**  
  Her API çağrısının zaman damgası `api_request_log.json` dosyasında saklanır. Böylece script restart edilse bile son 1 saatte yapılan API istekleri takip edilebilir.

- **Dinamik Rate Limit Kontrolü:**  
  - Eğer son 1 saatte 200 veya daha fazla API isteği yapılırsa, script 1 saat bekler.
  - Eğer 100 veya daha fazla API isteği yapılırsa, engelleme işlemleri durdurulur ve her 1 dakikada JSON dosyası kontrol edilerek istek sayısı 50’ye düştüğünde işlemler devam eder.
  - Her 1 dakikada API isteği sayısı loglanır.

## Hesap Güvenliği ve Alınan Önlemler

- **Challenge Yönetimi:**  
  Eğer Instagram, challenge (ChallengeRequired) durumu gösterirse, otomatik challenge çözümü denenmez. Bunun yerine, kullanıcıya:

  > "Lütfen Instagram hesabınıza gidip challenge'ı manuel olarak çözün ve scripti yeniden başlatın."

  şeklinde talimat verilir.

- **Kullanıcı Adı Doğrulaması:**  
  Blacklist dosyasındaki kullanıcı adları, geçerli bir formatta olup olmadıkları için kontrol edilir. Bu sayede hatalı veya geçersiz kullanıcı adlarının engellenmesi önlenir.

- **Güvenli API İstek Yönetimi:**  
  API çağrıları persist edilir, böylece script restart edilse bile son 1 saatte yapılan API istekleri doğru şekilde izlenir. Bu, Instagram’ın API rate limitlerine uygun davranmak için önemli bir önlemdir.

- **Log Filtreleme:**  
  "public_request" ve "JSONDecodeError" içeren log mesajları filtrelenir, böylece gereksiz hata mesajları loglarda görünmez.

## Detaylı Süre Loglaması

Her 10 başarılı engelleme işleminden sonra kalan engellenmemiş hesap sayısı ve tahmini süre hesaplanarak loglanır. Örneğin:

```
Kalan engellenmemiş hesap sayısı: 25. Tahmini süre: 12 dakika 30 saniye.
```

Bu bilgi, engelleme işlemlerinin tamamlanma süresine dair tahmini bir zaman verir.

## Ek Notlar

- **Kullanım Kolaylığı:**  
  Proje, teknik bilgisi az olan kullanıcıların bile rahatlıkla kullanabilmesi için adım adım ve detaylı loglarla çalışmaktadır.

- **Geliştirici Notları:**  
  - Challenge durumunda otomatik çözüm denenmez; manuel müdahale gereklidir.
  - `--request-limit` parametresi ile saatlik API istek limiti ayarlanabilir (varsayılan: 100).
  - Başarılı engelleme işlemleri sonrası 30 saniye, başarısız işlemler sonrası ise 60 saniye beklenir.
  - Her döngüde kalan engellenmemiş hesap sayısı ve tahmini süre detaylı olarak loglanır.

## İletişim

Herhangi bir sorun, öneri veya katkı için lütfen [tensorenes@gmail.com](mailto:tensorenes@gmail.com) adresine ulaşın.
