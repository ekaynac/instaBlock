
# Instagram Engelleme Aracı (CLI)

Bu proje, instagrapi kütüphanesini kullanarak Instagram hesaplarını otomatik olarak engellemek amacıyla geliştirilmiş bir CLI (Komut Satırı Arayüzü) aracıdır. Kod, hem manuel hem de otomatik challenge çözümünü (challenge required durumlarında) desteklemez; bu durumda kullanıcıya Instagram hesabınıza gidip challenge'ı manuel olarak çözmesi için talimat verir.

## İçerik

-   [Özellikler](#%C3%B6zellikler)
    
-   [Kurulum](#kurulum)
    
-   [Kullanım](#kullan%C4%B1m)
    
    -   [Giriş Parametreleri](#giri%C5%9F-parametreleri)
        
    -   [Blacklist Dosyası](#blacklist-dosyas%C4%B1)
        
    -   [Initial Blacklist Oluşturma](#initial-blacklist-olu%C5%9Fturma)
        
-   [Hesap Güvenliği ve Alınan Önlemler](#hesap-g%C3%BCvenli%C4%9Fi-ve-al%C4%B1nan-%C3%B6nlemler)
    
-   [API İstek Yönetimi](#api-i%CC%87stek-y%C3%B6netimi)
    
-   [Detaylı Süre Loglaması](#detayl%C4%B1-s%C3%BCre-loglamas%C4%B1)
    
-   [Geliştirici Notları](#geli%C5%9Ftirici-notlar%C4%B1)
    

## Özellikler

-   **Blacklist Temelli Engelleme:** Belirtilen bir TXT veya CSV dosyasındaki kullanıcı adlarına göre Instagram hesaplarını engeller.
    
-   **Initial Blacklist Oluşturma:** Belirli bir Instagram hesabının takip ettiklerinden otomatik olarak bir başlangıç blacklist'i oluşturur.
    
-   **API İstek Persistansı:** API isteklerinin zaman damgaları `api_request_log.json` dosyasında saklanır. Böylece script restart edildiğinde son 1 saat içinde yapılan istek sayısı hesaplanır.
    
-   **Dinamik Rate Limit Kontrolü:** Son 1 saatte yapılan API istekleri 200'ü aştığında script 1 saat bekler; 100'ün üzerinde istek yapıldıysa engelleme işlemleri durdurulur ve 1 dakikada bir kontrol edilerek istek sayısı 50'ye düştüğünde işlemlere devam edilir.
    
-   **Detaylı Loglama:** Her adım detaylı olarak Türkçe loglanır; kalan engellenecek hesap sayısı ve tahmini süre loglanır.
    
-   **Güvenlik Önlemleri:**
    
    -   Challenge durumunda (ChallengeRequired) kullanıcıya manuel çözüm talimatı verilir.
        
    -   Kullanıcı adları, belirli bir düzen (regex) ile doğrulanır.
        
    -   Public endpoint ile ilgili JSONDecodeError hataları loglanmaz.
        

## Kurulum

### Gereksinimler

-   Python 3.6+
    
-   [instagrapi](https://github.com/adw0rd/instagrapi) kütüphanesi
    

### Kurulum Adımları

1.  **Repository'yi Klonlayın:**
    
    bash
    
    Kopyala
    
    `git clone https://github.com/<yourusername>/InstaBlocker.git cd InstaBlocker` 
    
2.  **Gerekli Paketleri Yükleyin:**
    
    bash
    
    Kopyala
    
    `pip install instagrapi` 
    
3.  **(Opsiyonel) Sanal Ortam Oluşturun:**
    
    bash
    
    Kopyala
    
    `python -m venv venv source venv/bin/activate # Linux/Mac venv\Scripts\activate # Windows` 
    

## Kullanım

### Giriş Parametreleri

Script aşağıdaki parametreleri destekler:

-   `--username`: Instagram kullanıcı adınız (giriş yapmak için).
    
-   `--blacklist`: Engellenecek hesapların listesinin bulunduğu dosya (TXT veya CSV formatında).
    
-   `--init-blacklist`: Hedef hesabın takip ettiklerinden başlangıç blacklist'i oluşturmak için (URL veya kullanıcı adı şeklinde girin).
    
-   `--request-limit`: Saatlik API istek limiti (varsayılan 100). Bu değer, API isteklerinin dinamik yönetilmesi için kullanılır.
    

### Blacklist Dosyası

Blacklist dosyası iki formatta olabilir:

-   **TXT Dosyası:** Her satırda bir kullanıcı adı.
    
-   **CSV Dosyası:** En az `username` adlı bir sütun içermelidir.
    

Örnek CSV formatı:

csv

Kopyala

`username
user1
user2
user3` 

### Initial Blacklist Oluşturma

Eğer bir Instagram hesabının takip ettiği hesaplardan otomatik olarak başlangıç blacklist'i oluşturmak isterseniz, aşağıdaki komutu kullanın:

bash

Kopyala

`python boykot.py --username YOUR_USERNAME --init-blacklist https://www.instagram.com/target_account/` 

Bu komut, `target_account` hesabının takip ettiği tüm hesapları `blacklist_target_account.txt` adlı bir dosyaya kaydedecektir.

### Engelleme Modu

Engelleme modunu çalıştırmak için, blacklist dosyasını belirtmeniz gerekir:

bash

Kopyala

`python boykot.py --username YOUR_USERNAME --blacklist path/to/blacklist.txt --request-limit 100` 

Script, belirtilen blacklist dosyasındaki hesapları engellemeye başlayacak, API isteklerini persist edecek ve rate limit kontrollerini gerçekleştirecektir.

## Hesap Güvenliği ve Alınan Önlemler

-   **API İstek Persistansı:**  
    API isteklerinin zaman damgaları `api_request_log.json` dosyasında saklanır. Bu, scriptin restart edildiğinde son 1 saatte yapılan API çağrısı sayısını doğru bir şekilde takip etmesine olanak sağlar.
    
-   **Dinamik Rate Limiti:**  
    Belirlenen API istek limiti (örneğin, 100) aşıldığında, script engelleme işlemlerini durdurur ve her 1 dakikada bir JSON dosyasını kontrol ederek istek sayısının 50’ye düştüğünü gördüğünde devam eder. Bu, Instagram’ın API rate limitlerine uygun davranmak için alınan önemli bir önlemdir.
    
-   **Challenge Yönetimi:**  
    Eğer Instagram, challenge (ChallengeRequired) talep ederse, script hata detaylarını loglar ve kullanıcıya "Lütfen Instagram hesabınıza gidip challenge'ı manuel olarak çözün ve scripti yeniden başlatın." mesajı verir. Bu, otomatik challenge çözümünü denememekte, güvenlik nedeniyle manuel müdahaleyi tercih etmektedir.
    
-   **Kullanıcı Adı Doğrulaması:**  
    Blacklist dosyasındaki kullanıcı adları, regex kullanılarak doğrulanır. Böylece hatalı veya geçersiz kullanıcı adlarının işlenmesi engellenir.
    
-   **Hassas Log Filtreleme:**  
    Public endpoint’lerden kaynaklanan `JSONDecodeError` gibi istenmeyen log mesajları, `PublicRequestFilter` ile filtrelenir. Bu, logların gereksiz hata mesajlarıyla dolmasını engeller.
    

## API İstek Yönetimi

-   **Persistent API Log:**  
    Her API çağrısı zaman damgası ile kaydedilir ve `api_request_log.json` dosyasında saklanır. Böylece script yeniden başlatılsa bile son 1 saatte yapılan API çağrıları izlenir.
    
-   **Rate Limit Kontrolü:**  
    `check_rate_limit()` fonksiyonu, son 1 saatte yapılan API çağrısı sayısını kontrol eder.
    
    -   Eğer 200 veya daha fazla istek yapılmışsa, script 1 saat bekler.
        
    -   Eğer 100 veya daha fazla istek yapılmışsa, engelleme işlemleri durdurulur ve her 1 dakikada bir istek sayısı kontrol edilerek 50'ye düştüğünde devam edilir.
        
-   **Detaylı Loglama:**  
    Her 1 dakikada API istek sayısı loglanır. Ayrıca, her 10 başarılı bloklamada kalan engellenecek hesap sayısı ve tahmini süre loglanır.
    

## Detaylı Süre Loglaması

Her 10 başarılı bloklamadan sonra kalan hesap sayısı ve tahmini süre hesaplanarak loglanır. Örnek:

perl

Kopyala

`Kalan engellenmemiş hesap sayısı: 25. Tahmini süre: 12 dakika 30 saniye.` 

Bu bilgi, engelleme işlemlerinin ne kadar süreceğine dair tahmini bir zaman verir.

## Geliştirici Notları

-   **Challenge Durumu:**  
    ChallengeRequired durumunda, otomatik challenge çözümü denenmemektedir. Kullanıcıya manuel müdahale talimatı verilir.
    
-   **Log Filtresi:**  
    "public_request" ve "JSONDecodeError" içeren log mesajları, `PublicRequestFilter` sayesinde loglara yansıtılmaz.
    
-   **API İstek Limiti:**  
    `--request-limit` parametresi ile API istek limiti (saatlik) ayarlanabilir. Varsayılan değer 100’dür.
    
-   **Hata ve Uyarı Mesajları:**  
    Tüm hata, uyarı ve bilgi mesajları detaylı olarak Türkçe loglanır. Bu, özellikle teknik olmayan kullanıcıların süreci anlaması için faydalıdır.
