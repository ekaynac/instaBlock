import os
import csv
import time
import json
import logging
import argparse
import getpass
from datetime import datetime
from urllib.parse import urlparse
import re

from instagrapi import Client
from instagrapi.exceptions import (
    PleaseWaitFewMinutes,
    ClientError,
    ChallengeRequired
)

API_LOG_FILE = "api_request_log.json"
api_requests = []

# Logging filtresi: "public_request" ve "JSONDecodeError" içeren mesajları engeller
class PublicRequestFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        if "public_request" in msg and "JSONDecodeError" in msg:
            return False
        if "?__a=1&__d=dis" in msg:
            return False
        return True

def log_remaining_info(blacklist, already_blocked, average_time=30):
    remaining = len(set(blacklist) - already_blocked)
    estimated_seconds = remaining * average_time
    minutes = estimated_seconds // 60
    seconds = estimated_seconds % 60
    logging.info(f"Kalan engellenmemiş hesap sayısı: {remaining}. Tahmini süre: {int(minutes)} dakika {int(seconds)} saniye.")

def load_api_requests():
    if os.path.exists(API_LOG_FILE):
        try:
            with open(API_LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            logging.error(f"API log dosyası yüklenirken hata: {e}")
    return []

def save_api_requests(timestamps):
    try:
        with open(API_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(timestamps, f)
    except Exception as e:
        logging.error(f"API log dosyasına kaydedilirken hata: {e}")

def cleanup_api_requests():
    global api_requests
    current_time = time.time()
    api_requests = [t for t in api_requests if current_time - t < 3600]
    save_api_requests(api_requests)
    return api_requests

def record_api_request():
    global api_requests
    current_time = time.time()
    api_requests.append(current_time)
    cleanup_api_requests()
    return len(api_requests)

def check_rate_limit(remaining_to_block, request_limit):
    """
    API isteği yapılmadan önce, son 1 saat içindeki istek sayısını kontrol eder.
    - Eğer belirlenen istek sınırına ulaşılmışsa, engelleme işlemleri durdurulur ve
      her 1 dakikada JSON dosyası kontrol edilerek istek sayısı sınırın yarısına düştüğünde devam edilir.
    - Eğer engellenecek kalan hesap sayısından az istek yapılmışsa, direkt devam edilir.
    """
    global api_requests
    cleanup_api_requests()
    count = len(api_requests)
    if count >= request_limit:
        logging.info(f"Son 1 saat içinde {request_limit} API isteği yapıldı. Engelleme işlemleri durduruluyor, lütfen bekleyin...")
        while True:
            cleanup_api_requests()
            current_count = len(api_requests)
            logging.info(f"Son 1 saat içindeki API isteği sayısı: {current_count}")
            if current_count <= request_limit // 2 or current_count <= remaining_to_block:
                logging.info("API isteği sayısı sınırın yarısına veya engellenecek hesap sayısına düştü. Engelleme işlemlerine devam ediliyor.")
                break
            time.sleep(60)

def extract_username(input_value):
    if input_value.startswith("http"):
        parsed = urlparse(input_value)
        path = parsed.path.strip('/')
        return path.split('/')[0] if path else None
    return input_value

def validate_username(username):
    if not re.match(r'^[a-zA-Z0-9._]{1,30}$', username):
        raise ValueError(f"Invalid username: {username}")
    return username

def read_blacklist(file_path):
    accounts = []
    try:
        if file_path.endswith('.csv'):
            with open(file_path, newline='', encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if 'username' in row and row['username'].strip():
                        accounts.append(validate_username(row['username'].strip()))
        else:
            with open(file_path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        accounts.append(validate_username(line.strip()))
    except Exception as e:
        logging.error(f"Blacklist dosyası okunamadı: {e}")
    return accounts

def read_local_blocked_accounts(log_file):
    blocked = set()
    if os.path.exists(log_file):
        try:
            with open(log_file, newline='', encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    blocked.add(row.get('blocked_account', '').strip())
        except Exception as e:
            logging.error(f"Log dosyası okunamadı: {e}")
    return blocked

def log_blocked_account(log_file, target_username):
    fieldnames = ['blocked_account', 'date_time']
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_exists = os.path.exists(log_file)
    try:
        with open(log_file, 'a', newline='', encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow({'blocked_account': target_username, 'date_time': now})
    except Exception as e:
        logging.error(f"Log dosyasına yazılamadı: {e}")

def fetch_blocked_accounts(client, request_limit):
    blocked = set()
    try:
        check_rate_limit(len(blocked), request_limit)
        params = {"rank_token": client.uuid, "max_id": "0"}
        response = client.private_request("friendships/blocked_list/", params=params)
        record_api_request()
        for user in response.get("users", []):
            blocked.add(user.get("username"))
    except Exception as e:
        logging.warning(f"Instagram'dan engellenmiş hesaplar alınamadı (endpoint kullanılamıyor olabilir). Yerel log kullanılacak. Hata: {e}")
        return blocked
    return blocked

def get_user_id(client, target_username, request_limit):
    try:
        check_rate_limit(1, request_limit)
        user_info = client.user_info_by_username(target_username)
        record_api_request()
        return user_info.pk
    except ChallengeRequired as e:
        logging.error(f"{target_username} için challenge gerekli: {e}")
        logging.error("Lütfen Instagram hesabınıza gidip challenge'ı manuel olarak çözün ve scripti yeniden başlatın.")
        input("Challenge'ı çözdükten sonra devam etmek için Enter tuşuna basın...")
        return get_user_id(client, target_username, request_limit)
    except ClientError as e:
        logging.error(f"{target_username} için kullanıcı bilgileri alınamadı: {e}")
        return None
    except Exception as e:
        if "429" in str(e):
            logging.warning(f"{target_username} için 429 hatası alındı. 1 saat bekleniyor...")
            time.sleep(3600)
        else:
            logging.error(f"{target_username} için beklenmeyen hata: {e}")
        return None

def block_account(client, target_username, request_limit):
    user_id = get_user_id(client, target_username, request_limit)
    if user_id is None:
        return False
    try:
        check_rate_limit(1, request_limit)
        client.user_block(user_id)
        record_api_request()
        return True
    except PleaseWaitFewMinutes as e:
        logging.warning(f"{target_username} engellenirken rate limit hatası alındı: {e}")
        logging.info("Rate limit nedeniyle 1 saat bekleniyor...")
        time.sleep(3600)
        return False
    except Exception as e:
        if "429" in str(e):
            logging.warning(f"{target_username} engellenirken 429 hatası alındı. 1 saat bekleniyor...")
            time.sleep(3600)
        else:
            logging.error(f"{target_username} engellenirken hata oluştu: {e}")
        return False

def create_initial_blacklist(client, target_account, request_limit):
    try:
        target_user_id = client.user_id_from_username(target_account)
    except Exception as e:
        logging.error(f"{target_account} için kullanıcı ID'si alınamadı: {e}")
        return
    try:
        followings = client.user_following(target_user_id)
        usernames = [profile.username for profile in followings.values()]
        filename = f"blacklist_{target_account}.txt"
        with open(filename, 'w', encoding="utf-8") as f:
            for username in usernames:
                f.write(username + "\n")
        logging.info(f"Blacklist oluşturuldu: {len(usernames)} hesap {filename} dosyasına kaydedildi.")
    except Exception as e:
        logging.error(f"{target_account} için takip listesini alırken hata oluştu: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Instagram Engelleme Aracı (CLI) - instagrapi kullanılarak\n"
                    "Modlar:\n"
                    "• Engelleme modu: Belirtilen blacklist dosyasındaki hesapları engeller.\n"
                    "• Initial Blacklist modu: Hedef hesabın takip ettiklerinden blacklist oluşturur."
    )
    parser.add_argument('--username', required=True, help="Instagram kullanıcı adınız (giriş için)")
    parser.add_argument('--blacklist', help="Engellenecek hesapların listesinin bulunduğu dosya (TXT veya CSV)")
    parser.add_argument('--init-blacklist', help="Hedef hesabın takip ettiklerinden başlangıç blacklist'i oluştur (URL veya kullanıcı adı)")
    parser.add_argument('--request-limit', type=int, default=100, help="Saatlik API istek limiti (varsayılan: 100)")
    args = parser.parse_args()

    password = getpass.getpass(prompt="Instagram şifrenizi giriniz: ")

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # Tüm handler'lara PublicRequestFilter ekleniyor
    logger = logging.getLogger()
    for handler in logger.handlers:
        handler.addFilter(PublicRequestFilter())
    logging.info("Instagram Engelleme Aracı başlatıldı.")

    global api_requests
    api_requests = load_api_requests()

    client = Client()
    try:
        client.login(args.username, password)
    except Exception as e:
        logging.error(f"Giriş başarısız: {e}")
        return

    logging.info("Giriş başarılı.")

    if args.init_blacklist:
        target_account = extract_username(args.init_blacklist)
        if not target_account:
            logging.error("Geçerli bir kullanıcı adı bulunamadı.")
            return
        logging.info(f"{target_account} hesabının takip listesinden initial blacklist oluşturuluyor...")
        create_initial_blacklist(client, target_account, args.request_limit)
        return

    if not args.blacklist:
        logging.error("Engelleme modu için --blacklist parametresi ile bir dosya belirtilmelidir.")
        return

    log_file = f"blocked_{args.username}.csv"
    blacklist = read_blacklist(args.blacklist)
    remaining_accounts = set(blacklist)
    logging.info(f"Blacklist yüklendi: {len(blacklist)} hesap bulundu.")
    
    blocked_accounts_local = read_local_blocked_accounts(log_file)
    already_blocked = blocked_accounts_local  # Sadece yerel logtan alınanları kullanıyoruz, API'dan alınamazsa

    logging.info(f"Toplam engellenmiş hesap (yerel): {len(already_blocked)}")
    
    remaining_to_block = remaining_accounts - already_blocked
    logging.info(f"Engellenecek {len(remaining_to_block)} hesap kaldı.")

    successful_blocks = 0
    for account in blacklist:
        if account in already_blocked:
            continue
        logging.info(f"{account} engelleniyor...")
        success = block_account(client, account, args.request_limit)
        if success:
            logging.info(f"{account} başarıyla engellendi.")
            log_blocked_account(log_file, account)
            already_blocked.add(account)
            successful_blocks += 1
            if successful_blocks % 10 == 0:
                log_remaining_info(blacklist, already_blocked, average_time=30)
            time.sleep(30)  # Başarılı bloklamadan sonra 30 saniye bekle
        else:
            logging.warning(f"{account} engellenemedi. 60 saniye sonra tekrar deneniyor.")
            time.sleep(60)

    while True:
        logging.info("Blacklist dosyası yeniden okunuyor...")
        blacklist = read_blacklist(args.blacklist)
        remaining_to_block = set(blacklist) - already_blocked
        logging.info(f"Engellenecek {len(remaining_to_block)} hesap kaldı.")
        successful_blocks = 0
        for account in blacklist:
            if account in already_blocked:
                continue
            logging.info(f"{account} engelleniyor...")
            success = block_account(client, account, args.request_limit)
            if success:
                logging.info(f"{account} başarıyla engellendi.")
                log_blocked_account(log_file, account)
                already_blocked.add(account)
                successful_blocks += 1
                if successful_blocks % 10 == 0:
                    log_remaining_info(blacklist, already_blocked, average_time=30)
                time.sleep(30)  # Başarılı bloklamadan sonra 30 saniye bekle
            else:
                logging.warning(f"{account} engellenemedi. 60 saniye sonra tekrar deneniyor.")
                time.sleep(60)

        logging.info("Blacklist kontrolü tamamlandı. 5 dakika sonra yeniden denenecek.")
        time.sleep(300)

if __name__ == "__main__":
    main()