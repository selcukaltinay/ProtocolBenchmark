# Data Quality Issues - LPWAN Protocol Benchmark

## Summary
Test sonuçlarında 3 kritik veri tutarlılık sorunu tespit edildi ve düzeltildi.

## ✅ ÇÖZÜLEN SORUNLAR

## 1. ✅ Duplicate Detection Eksikliği (>100% Delivery Ratios) - ÇÖZÜLDÜ

### Problem
Protokoller retry mekanizması kullanarak kayıp paketleri yeniden gönderiyor, ancak `run_experiments.py` aynı sequence numarasına sahip mesajları birden fazla sayıyordu.

### Örnek Hata
```
Expected: 1000 mesaj
Received: 1217 mesaj (aynı sequence numaralarının tekrarları)
Delivery Ratio: 121.7% ❌
```

### Root Cause
`run_experiments.py` satır 144 (ESKİ):
```python
received_count = len(df)  # Tüm satırları sayıyor, unique değil!
```

### ✅ Uygulanan Fix
`run_experiments.py` satır 153 (YENİ):
```python
# Unique sequence numaralarını say
received_count = df['sequence'].nunique() if 'sequence' in df.columns else len(df)
delivery_ratio = (received_count / expected_count) * 100.0
```

### Sonuç
- Artık duplicate mesajlar sayılmıyor
- Delivery ratio max %100 olabilir
- Gerçek ilk teslimat oranı doğru hesaplanıyor

---

## 2. ✅ HTTP Survivor Bias (Missing Tests) - ÇÖZÜLDÜ

### Problem
HTTP testlerinin 206'sı (%58) hiç kaydedilmemiş. Sadece başarılı testler CSV'ye yazılmış, bu da sonuçları olduğundan iyi gösteriyordu.

### Kanıt (ESKİ)
```
MQTT QoS0:  355 test
MQTT QoS1:  356 test
AMQP QoS0:  355 test
HTTP:       149 test ❌ (206 test kayıp!)
```

### Root Cause
1. `HTTPProducer.java` timeout handling yoktu - sonsuz bekleme
2. `run_experiments.py` hatalı testleri CSV'ye yazmıyordu

### ✅ Uygulanan Fixler

**1. HTTPProducer.java - Timeout Eklendi:**
```java
// YENİ: Timeout config
RequestConfig config = RequestConfig.custom()
    .setConnectTimeout(Timeout.ofSeconds(10))
    .setResponseTimeout(Timeout.ofSeconds(30))
    .build();

CloseableHttpClient client = HttpClients.custom()
    .setDefaultRequestConfig(config)
    .build();
```

**2. run_experiments.py - Failed Tests Kaydediliyor:**
```python
# Her test için default değerler
delivery_ratio = 0.0
test_status = "FAILED"

# Başarılı ise SUCCESS, değilse NO_DATA/ERROR
# Her durumda CSV'ye yazılıyor (satır 167-192)

# YENİ KOLONLAR:
- Status: "SUCCESS", "NO_DATA", "ERROR: ..."
- ReceivedCount: Alınan mesaj sayısı
- ExpectedCount: Beklenen mesaj sayısı
```

### Sonuç
- Artık tüm testler (başarılı/başarısız) kaydediliyor
- HTTP timeout olan testler "Status: ERROR" ile görünecek
- Gerçek başarı/başarısızlık oranları izlenebilir

---

## 3. CoAP Performance Anomaly (High Latency)

### Problem
CoAP (UDP-based, lightweight) beklenenden YAVAŞ çalışıyor.

### Karşılaştırma
```
MQTT (TCP-based):  1.7-3.0 ms latency
CoAP (UDP-based):  7.0-20.0 ms latency ❌
```

### Beklenen
CoAP, UDP tabanlı ve daha hafif olduğu için MQTT'den daha hızlı olmalı.

### Olası Nedenler
1. Python `aiocoap` kütüphanesi performans sorunu?
2. CoAP confirmation mekanizması (CON vs NON messages)?
3. Network emulation CoAP paketlerini farklı mı etkiliyor?
4. Buffer/queue boyutları CoAP için optimize değil?

### Önerilen İnceleme
1. CoAP CON vs NON message modlarını karşılaştır
2. `aiocoap` profiling yap
3. Wireshark ile paket analizi
4. Java CoAP implementasyonu dene (Californium library)

---

## AÇIK SORUNLAR (İnceleme Gerekiyor)

## 4. Missing Metric: First-Attempt vs Retry Success

### Problem
Şu anki metrikler ilk denemede başarı ile retry sonrası başarıyı ayırt edemiyor.

### Neden Önemli
```
Scenario A: %100 first-attempt delivery (ideal)
Scenario B: %60 first-attempt, %40 retry success (ağ sorunlu)
```

Her ikisi de %100 delivery gösteriyor ama Scenario B ağ kalitesini yansıtmıyor.

### Önerilen Metrik
```python
# Her mesaj için:
- first_attempt_delivery: İlk göndermede başarılı
- retry_count: Kaç kez retry edildi
- total_attempts: Toplam deneme sayısı
```

**Durum**: Gelecek iyileştirme (düşük öncelik)

---

## ÖZET

### ✅ Çözülen Sorunlar (Kod Değişiklikleri Yapıldı)
1. **Duplicate Detection**: Artık unique sequence numaraları sayılıyor
2. **Timeout Handling**: TÜM protokollere timeout eklendi
   - MQTT: 10s connection, 15s wait timeout
   - AMQP: 10s connection, 10s handshake, 30s heartbeat
   - HTTP: 10s connection, 30s response timeout
   - CoAP: 30s request timeout
   - XMPP: 15s connection timeout
3. **Failed Test Recording**: Tüm testler (başarılı/başarısız) CSV'ye yazılıyor

### 📊 Yeni CSV Kolonları
- `Status`: Test durumu (SUCCESS, NO_DATA, ERROR)
- `ReceivedCount`: Alınan unique mesaj sayısı
- `ExpectedCount`: Beklenen mesaj sayısı

### 🔄 Sonraki Adımlar
1. **Java build yenile**: `cd java_bench && docker build -t lpwan-java-bench .`
2. **Testleri yeniden çalıştır**: `python3 run_experiments.py`
3. **Yeni sonuçları incele**: Status kolonu ile başarı/başarısızlık oranlarını analiz et
4. **CoAP latency investigation**: Hala beklemede (Python aiocoap profiling gerekebilir)

### ⚠️ Önemli Not
Mevcut results/*.csv dosyaları ESKİ formatla! Yeni testler çalıştırıldıktan sonra:
- Tüm protokollerde ~355 test olmalı (eksik test olmamalı)
- Delivery ratio max %100 olmalı (>100% olmamalı)
- Status kolonu ile hangi testlerin başarısız olduğu görülebilir
